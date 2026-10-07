"""Phase 4 guided-scenario contract, validation, and replay tests."""

import copy
import json
import os
import sys
import unittest
from unittest.mock import patch


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.catalog_contracts import VerificationState
from netspout_core.models import TelemetryTransportConfig
from netspout_core.pack_contracts import (
    GuidedScenarioManifest,
    PackRegistry,
    ReplayPolicy,
    ScenarioVisualization,
    evaluate_guided_scenario_completeness,
)
from netspout_core.unified_generation import (
    GenerationMode,
    UnifiedGenerationRequest,
    UnifiedGenerationService,
)


class FakeDispatcher:
    def dispatch_log(self, entry, transport):
        return {"hec": {"success": True, "message": "accepted"}}


class TestPhase4GuidedScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(
            os.path.join(REPO_ROOT, "catalog", "extension_packs.json"),
            encoding="utf-8",
        ) as handle:
            cls.registry_data = json.load(handle)
        cls.registry = PackRegistry.model_validate(cls.registry_data)
        cls.scenario = cls.registry._resources()["scenarios"][0]
        cls.transport = TelemetryTransportConfig(
            hec_enabled=True,
            hec_url="https://splunk.example.invalid:8088/services/collector",
            hec_token="runtime-test-value",
            hec_index="idx_network_ops",
            hec_ssl_verify=True,
            hec_allow_insecure_tls=False,
        )

    def test_01_valid_guided_scenario_has_all_completeness_sections(self):
        result = evaluate_guided_scenario_completeness(
            self.scenario,
            executable=True,
            provenance_available=True,
            verification_state=VerificationState.PARTIALLY_VERIFIED,
        )
        self.assertEqual(result["passed"], result["total"])
        self.assertEqual(result["total"], 12)
        self.assertEqual(result["state"], "PARTIAL")

    def test_02_incomplete_scenario_stays_partial_without_schema_fabrication(self):
        incomplete = self.scenario.model_copy(
            update={
                "technical_description": None,
                "baseline_description": None,
                "investigation_steps": [],
                "validation_expectations": [],
                "replay_policy": None,
            }
        )
        result = evaluate_guided_scenario_completeness(
            incomplete,
            executable=True,
            provenance_available=True,
            verification_state=VerificationState.VERIFIED,
        )
        self.assertEqual(result["state"], "PARTIAL")
        self.assertFalse(result["checks"]["story"])
        self.assertFalse(result["checks"]["investigation"])
        self.assertFalse(result["checks"]["validation"])
        self.assertFalse(result["checks"]["replay_reset"])

    def test_03_invalid_relationship_reference_fails_closed(self):
        data = self.scenario.model_dump(mode="json")
        data["relationships"][0]["target_node_id"] = "missing-node"
        with self.assertRaisesRegex(ValueError, "missing-node"):
            GuidedScenarioManifest.model_validate(data)

    def test_04_missing_incident_path_node_fails_closed(self):
        data = self.scenario.model_dump(mode="json")
        data["incident_path"].append("missing-node")
        with self.assertRaisesRegex(ValueError, "missing-node"):
            GuidedScenarioManifest.model_validate(data)

    def test_05_invalid_timeline_entity_reference_fails_closed(self):
        data = self.scenario.model_dump(mode="json")
        data["timeline"][0]["entity_state_changes"] = {"missing-node": "normal"}
        with self.assertRaisesRegex(ValueError, "missing-node"):
            GuidedScenarioManifest.model_validate(data)

    def test_06_invalid_timeline_telemetry_reference_fails_closed(self):
        data = self.scenario.model_dump(mode="json")
        data["timeline"][0]["telemetry_state_changes"] = {
            "missing-source": "ACTIVE"
        }
        with self.assertRaisesRegex(ValueError, "missing-source"):
            GuidedScenarioManifest.model_validate(data)

    def test_07_invalid_investigation_recipe_reference_fails_closed(self):
        data = copy.deepcopy(self.registry_data)
        scenario = next(
            pack["scenarios"][0] for pack in data["packs"] if pack["scenarios"]
        )
        scenario["investigation_steps"][0]["recipe_id"] = "missing-recipe"
        with self.assertRaisesRegex(ValueError, "missing-recipe"):
            PackRegistry.model_validate(data)

    def test_08_curated_visualization_requires_explicit_layout(self):
        with self.assertRaisesRegex(ValueError, "layout reference"):
            ScenarioVisualization.model_validate(
                {"mode": "CURATED", "direction": "LEFT_TO_RIGHT"}
            )
        automatic = ScenarioVisualization.model_validate({"mode": "AUTOMATIC"})
        self.assertIsNone(automatic.curated_layout_ref)

    def test_09_replay_policy_preserves_history_and_new_identity(self):
        with self.assertRaisesRegex(ValueError, "new run"):
            ReplayPolicy.model_validate(
                {"creates_new_run_id": False, "preserves_history": True}
            )
        service = UnifiedGenerationService(dispatcher=FakeDispatcher())
        request = UnifiedGenerationRequest(
            mode=GenerationMode.SCENARIO,
            selection_id="rfc5424-link-state-lifecycle",
            count=6,
            rate_eps=100,
            transport_id="transport-local-hec",
            destination_id="destination-local-docker-splunk",
        )
        with patch.object(service, "_check_hec", return_value=(True, "HTTP 200")):
            first = service.run(request, self.transport)
            replay = service.run(request, self.transport)
        self.assertNotEqual(first.run_id, replay.run_id)
        self.assertIn(first.run_id, service.runs)
        self.assertIn(replay.run_id, service.runs)
        self.assertNotEqual(first.events[0].raw, replay.events[0].raw)

    def test_10_runtime_validation_changes_only_from_evidence(self):
        service = UnifiedGenerationService(dispatcher=FakeDispatcher())
        request = UnifiedGenerationRequest(
            mode=GenerationMode.SCENARIO,
            selection_id="rfc5424-link-state-lifecycle",
            count=6,
            rate_eps=100,
            transport_id="transport-local-hec",
            destination_id="destination-local-docker-splunk",
        )
        with patch.object(service, "_check_hec", return_value=(True, "HTTP 200")):
            run = service.run(request, self.transport)
        initial = {item.evidence_stage: item.state.value for item in run.validation}
        self.assertEqual(initial["GENERATED"], "PROVEN")
        self.assertEqual(initial["SPLUNK_OBSERVED"], "PENDING")
        with patch.object(
            service,
            "_search_splunk",
            return_value=(6, "Authenticated Splunk search proved indexed observation."),
        ):
            observed = service.observe(run.run_id, self.transport)
        final = {item.evidence_stage: item.state.value for item in observed.validation}
        self.assertEqual(final["SPLUNK_OBSERVED"], "PROVEN")
        self.assertEqual(final["SOURCETYPE_VERIFIED"], "PROVEN")

    def test_11_capability_exposes_guided_workflow_without_second_catalog(self):
        service = UnifiedGenerationService(dispatcher=FakeDispatcher())
        capabilities = service.capabilities()
        self.assertEqual(
            capabilities["guided_workflow"],
            ["UNDERSTAND", "PREPARE", "RUN", "OBSERVE", "INVESTIGATE", "VALIDATE"],
        )
        scenario = capabilities["scenarios"][0]
        self.assertEqual(scenario["guided_completeness"]["state"], "PARTIAL")
        self.assertEqual(scenario["guided_completeness"]["passed"], 12)
        self.assertEqual(len(service.registry.packs), 6)
        self.assertIn(
            "cisco-phase8c-domain-references",
            {item.pack_id for item in service.registry.packs},
        )

    def test_12_scenario_uses_neutral_metadata_and_no_vendor_renderer_key(self):
        data = self.scenario.model_dump(mode="json")
        self.assertEqual(data["visualization"]["mode"], "AUTOMATIC")
        self.assertNotIn("renderer", data)
        self.assertNotIn("logo", json.dumps(data).lower())
        self.assertTrue(all(node["node_id"] for node in data["nodes"]))


if __name__ == "__main__":
    unittest.main()
