import json
import re
import tempfile
import time
import unittest
from collections import Counter
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from netspout_core.cisco_scenario_factory import (
    CiscoScenarioFactoryService,
    ScenarioDefinition,
    ScenarioFactoryCatalog,
    ScenarioMaturity,
)
from netspout_core.scenario_studio import ScenarioStudioService, StudioScenarioPack


class TestPhase8Cisco100Factory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.path = cls.root / "catalog" / "cisco_100_scenarios.json"
        cls.service = CiscoScenarioFactoryService(cls.path)
        cls.catalog = cls.service.catalog
        cls.client = TestClient(app)

    def test_exact_100_and_20_per_domain(self):
        self.assertEqual(len(self.catalog.scenarios), 100)
        self.assertEqual(
            Counter(item.domain for item in self.catalog.scenarios),
            Counter(self.catalog.domain_targets),
        )
        self.assertEqual(set(self.catalog.domain_targets.values()), {20})

    def test_ids_are_unique_stable_and_domain_scoped(self):
        ids = [item.scenario_id for item in self.catalog.scenarios]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            Counter(item.scenario_id.split("-")[1] for item in self.catalog.scenarios),
            {"ENT": 20, "SP": 20, "DC": 20, "SEC": 20, "CRI": 20},
        )
        for item in self.catalog.scenarios:
            self.assertRegex(item.scenario_id, r"^C100-(ENT|SP|DC|SEC|CRI)-\d{3}$")
            changed = item.model_copy(update={"title": f"{item.title} revised"})
            self.assertEqual(changed.scenario_id, item.scenario_id)

    def test_required_contract_is_present_for_every_definition(self):
        required = set(ScenarioDefinition.model_fields)
        for item in self.catalog.scenarios:
            self.assertEqual(set(item.model_dump()), required)
            self.assertTrue(item.story)
            self.assertTrue(item.technical_objective)
            self.assertTrue(item.business_impact)
            self.assertTrue(item.timeline)

    def test_catalog_has_no_placeholder_or_numbered_filler_titles(self):
        titles = [item.title for item in self.catalog.scenarios]
        self.assertEqual(len(titles), len(set(titles)))
        prohibited = re.compile(r"\b(?:placeholder|lorem|tbd|todo|scenario\s*\d+)\b", re.I)
        for item in self.catalog.scenarios:
            self.assertIsNone(prohibited.search(item.title))
            self.assertGreaterEqual(len(item.technical_objective), 60)

    def test_actual_maturity_counts_are_computed(self):
        summary = self.catalog.summary()
        self.assertEqual(summary["maturity"]["CANDIDATE"], 70)
        self.assertEqual(summary["maturity"]["RESEARCH_REQUIRED"], 25)
        self.assertEqual(summary["maturity"]["GOLDEN"], 5)
        for maturity in (
            "RESEARCHED",
            "CONTRACTED",
            "FORMAT_VALIDATED",
            "RUNTIME_VALIDATED",
            "SPLUNK_VALIDATED",
            "UNSUPPORTED",
            "BLOCKED",
        ):
            self.assertEqual(summary["maturity"][maturity], 0)

    def test_direct_candidate_to_golden_promotion_fails(self):
        with self.assertRaisesRegex(ValueError, "advance exactly one evidence gate"):
            self.service.validate_promotion("C100-ENT-002", ScenarioMaturity.GOLDEN)

    def test_contracted_to_splunk_validated_promotion_fails(self):
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        golden = next(item for item in payload["scenarios"] if item["maturity"] == "GOLDEN")
        golden["maturity"] = "CONTRACTED"
        golden["execution_enabled"] = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            service = CiscoScenarioFactoryService(path)
            with self.assertRaisesRegex(ValueError, "advance exactly one evidence gate"):
                service.validate_promotion(
                    "C100-SP-001", ScenarioMaturity.SPLUNK_VALIDATED
                )

    def test_schema_rejects_missing_researched_evidence(self):
        candidate = next(
            item for item in self.catalog.scenarios if item.maturity == ScenarioMaturity.CANDIDATE
        )
        payload = candidate.model_dump(mode="json")
        payload["maturity"] = "RESEARCHED"
        with self.assertRaisesRegex(ValidationError, "evidence and telemetry candidates"):
            ScenarioDefinition.model_validate(payload)

    def test_research_required_generation_fails_closed(self):
        for scenario_id in ("C100-ENT-016", "C100-SP-020", "C100-SEC-018"):
            with self.assertRaisesRegex(ValueError, "No fallback event"):
                self.service.execution_decision(scenario_id)
            scenario = self.service.scenario(scenario_id)["scenario"]
            self.assertEqual(scenario["maturity"], "RESEARCH_REQUIRED")
            self.assertFalse(scenario["execution_enabled"])
            self.assertEqual(scenario["sourcetypes"], [])
            self.assertEqual(scenario["splunk_integrations"], [])
            self.assertTrue(
                any(
                    item["scenario_id"] == scenario_id
                    for item in self.service.view()["research_queue"]
                )
            )

    def test_every_declared_research_gap_is_actionable(self):
        expected = {
            (scenario.scenario_id, gap)
            for scenario in self.catalog.scenarios
            for gap in scenario.research_gaps
        }
        observed = {
            (item.scenario_id, item.missing_claim)
            for item in self.catalog.research_queue
        }
        self.assertEqual(observed, expected)
        research_ids = [item.research_id for item in self.catalog.research_queue]
        self.assertEqual(len(research_ids), len(set(research_ids)))

    def test_golden_delegates_to_existing_guided_runtime(self):
        decision = self.service.execution_decision("C100-SP-001")
        self.assertEqual(
            decision["runtime_scenario_id"],
            "test-correlated-interface-degradation",
        )
        self.assertEqual(
            decision["delegation"], "GUIDED_SCENARIO_EXPERIENCE"
        )

    def test_one_contract_set_is_reused_without_copying(self):
        asset = next(
            item
            for item in self.catalog.shared_assets
            if item.asset_id == "cisco-ios-xr-interface-contract-set"
        )
        self.assertEqual(
            asset.scenario_ids,
            ["C100-SP-001", "C100-SP-002", "C100-SP-005"],
        )
        contracts = [
            self.service.scenario(scenario_id)["scenario"]["source_contracts"]
            for scenario_id in asset.scenario_ids
        ]
        self.assertTrue(all(value == contracts[0] for value in contracts[1:]))

    def test_dependency_change_identifies_full_revalidation_impact(self):
        impact = self.service.affected_scenarios(
            "native-cisco-ios-xr-interface-syslog"
        )
        self.assertEqual(
            impact["affected_scenario_ids"],
            ["C100-SP-001", "C100-SP-002", "C100-SP-005"],
        )
        self.assertIn("cisco-ios-xr-coverage", impact["affected_product_packs"])
        self.assertIn(
            "investigate-correlated-interface-degradation",
            impact["affected_investigation_packs"],
        )
        self.assertEqual(
            impact["required_revalidation"],
            ["STATIC", "FORMAT", "RUNTIME", "SPLUNK", "GUIDED_LAB"],
        )

    def test_conflicting_reused_contract_is_rejected(self):
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        scenario = next(
            item for item in payload["scenarios"] if item["scenario_id"] == "C100-SP-002"
        )
        scenario["native_transports"] = ["transport-native-syslog-tcp"]
        with self.assertRaisesRegex(ValidationError, "contract contradiction"):
            ScenarioFactoryCatalog.model_validate(payload)

    def test_production_portable_spl_has_no_simulation_metadata(self):
        forbidden = ("netspout_run_id", "netspout_scenario_id", "netspout_phase")
        for scenario in self.catalog.scenarios:
            for query in scenario.production_portability.production_portable_spl:
                self.assertFalse(any(field in query for field in forbidden))

    def test_mixed_vendor_scenario_is_definition_only_and_core_neutral(self):
        mixed = self.service.scenario("C100-CRI-014")["scenario"]
        self.assertIn("Cisco Campus", mixed["technologies"])
        self.assertIn("Palo Alto Networks", mixed["technologies"])
        self.assertIn("AWS", mixed["technologies"])
        self.assertFalse(mixed["execution_enabled"])
        for filename in (
            "unified_generation.py",
            "native_runtime.py",
            "scenario_studio.py",
        ):
            text = (self.root / "src" / "netspout_core" / filename).read_text(
                encoding="utf-8"
            )
            self.assertNotRegex(text, r'if\s+vendor\s*==\s*["\'](?:cisco|Cisco)')

    def test_studio_clones_multiple_domains_without_promoting_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            studio = ScenarioStudioService(storage_dir=directory)
            for scenario_id in ("C100-ENT-001", "C100-DC-001", "C100-SEC-001"):
                definition = self.service.scenario(scenario_id)["scenario"]
                draft = studio.clone_definition(definition)
                fingerprint = draft.definition_contract_fingerprint
                transition = draft.timeline[1]
                changed_state = transition.state_changes[0].model_copy(
                    update={"value": "SEVERELY_IMPAIRED"}
                )
                changed_transition = transition.model_copy(
                    update={"state_changes": [changed_state]}
                )
                changed_entity = draft.entities[0].model_copy(
                    update={"x": 42.0, "y": 84.0}
                )
                draft = draft.model_copy(
                    update={
                        "timeline": [
                            draft.timeline[0],
                            changed_transition,
                            draft.timeline[2],
                        ],
                        "entities": [changed_entity, *draft.entities[1:]],
                    }
                )
                saved = studio.save_pack(draft)
                self.assertTrue(saved.definition_only)
                self.assertEqual(
                    saved.definition_contract_fingerprint, fingerprint
                )
                self.assertEqual(
                    saved.timeline[1].state_changes[0].value,
                    "SEVERELY_IMPAIRED",
                )
                self.assertEqual(saved.entities[0].x, 42.0)
            reloaded = ScenarioStudioService(storage_dir=directory)
            self.assertEqual(len(reloaded.list_packs()), 3)
            self.assertTrue(all(item.definition_only for item in reloaded.list_packs()))

    def test_studio_definition_contract_is_immutable_and_api_adapter_works(self):
        definition = self.service.scenario("C100-SP-002")["scenario"]
        with tempfile.TemporaryDirectory() as directory:
            draft = ScenarioStudioService(storage_dir=directory).clone_definition(
                definition
            )
        payload = draft.model_dump(mode="json")
        payload["definition_contract_ids"].append("invented-contract")
        with self.assertRaisesRegex(
            ValidationError, "structural contract fingerprint changed"
        ):
            StudioScenarioPack.model_validate(payload)
        response = self.client.post(
            "/api/cisco100/scenarios/C100-CRI-014/studio-draft"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["definition_only"])
        self.assertEqual(response.json()["source_ids"], [])
        self.assertTrue(response.json()["execution_blockers"])

    def test_golden_definition_clones_its_executable_runtime_contract(self):
        response = self.client.post(
            "/api/cisco100/scenarios/C100-DC-001/studio-draft"
        )
        self.assertEqual(response.status_code, 200, response.text)
        draft = response.json()
        self.assertFalse(draft["definition_only"])
        self.assertEqual(draft["cloned_from_scenario_id"], "C100-DC-001")
        self.assertEqual(
            draft["source_ids"], ["cisco-nx-os-interface-syslog"]
        )
        self.assertTrue(draft["contract_fingerprints"])
        self.assertTrue(draft["timeline"])

    def test_cim_is_independent_and_not_promoted(self):
        for scenario in self.catalog.scenarios:
            self.assertNotIn(
                "RUNTIME_VALIDATED",
                {value.value for value in scenario.cim_relationships.values()},
            )
        golden = self.service.scenario("C100-SP-001")["scenario"]
        self.assertEqual(set(golden["cim_relationships"].values()), {"NOT_ESTABLISHED"})

    def test_api_filters_matrix_dependencies_and_blocking(self):
        response = self.client.get(
            "/api/cisco100", params={"domain": "Enterprise Networking"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["filter_result_count"], 20)
        matrix = self.client.get("/api/cisco100/matrix")
        self.assertEqual(matrix.status_code, 200, matrix.text)
        self.assertEqual(len(matrix.json()["rows"]), 100)
        dependency = self.client.get(
            "/api/cisco100/dependencies/native-cisco-ios-xr-interface-syslog"
        )
        self.assertTrue(dependency.json()["revalidation_required"])
        blocked = self.client.post("/api/cisco100/scenarios/C100-SP-020/execute")
        self.assertEqual(blocked.status_code, 409)
        self.assertIn("No fallback event", blocked.json()["detail"])

    def test_api_rejects_invalid_promotion(self):
        response = self.client.post(
            "/api/cisco100/scenarios/C100-ENT-002/promotions/GOLDEN"
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("advance exactly one evidence gate", response.json()["detail"])

    def test_catalog_filter_matrix_and_dependency_performance(self):
        start = time.perf_counter()
        for _ in range(100):
            self.service.view(domain="Security & SASE", maturity="CANDIDATE")
            self.service.coverage_matrix()
            self.service.affected_scenarios(
                "native-cisco-ios-xr-interface-syslog"
            )
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertLess(elapsed_ms, 1000)

    def test_privacy_uses_reserved_or_fictional_identifiers(self):
        serialized = self.path.read_text(encoding="utf-8")
        self.assertNotRegex(serialized, r"\b(?:AKIA|ghp_|sk_live_|AIza)")
        self.assertNotIn("-----BEGIN PRIVATE KEY-----", serialized)
        self.assertNotIn("-----BEGIN CERTIFICATE-----", serialized)
        self.assertNotRegex(serialized, r"https?://[^\" ]*\\.cisco\\.com/internal")
        for scenario in self.catalog.scenarios:
            if scenario.scenario_id == "C100-SP-001":
                self.assertEqual(
                    scenario.entities,
                    [
                        "cisco-asr9k-pe1",
                        "HundredGigE0/0/0/1",
                        "bundled-syslog-receiver",
                        "bundled-snmp-receiver",
                        "bundled-gnmi-subscriber",
                        "test-local-splunk.invalid",
                    ],
                )
            else:
                self.assertTrue(
                    all(
                        entity.endswith(".example") or entity.endswith(".invalid")
                        for entity in scenario.entities
                    )
                )


if __name__ == "__main__":
    unittest.main()
