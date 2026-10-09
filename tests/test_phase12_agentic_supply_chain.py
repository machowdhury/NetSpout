import json
import tempfile
import unittest

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.phase12_security_packs import (
    SOURCE_CONFIG,
    build_phase12_state_plan,
    generate_phase12_event,
    validate_phase12_event,
)
from netspout_core.scenario_studio import ScenarioStudioService
from netspout_core.unified_generation import UnifiedGenerationService


def _phase12_scenarios(catalog):
    registry = catalog.get_extension_pack_registry()
    return {
        scenario["scenario_id"]: scenario
        for pack in registry["packs"]
        if pack["pack_id"].startswith("netspout-phase12-")
        for scenario in pack["scenarios"]
    }


class Phase12SecurityPackTests(unittest.TestCase):
    def test_registry_has_13_reference_scenarios_and_three_pack_architectures(self):
        catalog = NetSpoutCatalog()
        registry = catalog.get_extension_pack_registry()
        packs = {
            item["pack_id"]: item
            for item in registry["packs"]
            if item["pack_id"].startswith("netspout-phase12-")
        }
        scenarios = _phase12_scenarios(catalog)

        self.assertEqual(set(packs), {
        "netspout-phase12-agentic-ai-security",
        "netspout-phase12-software-supply-chain",
        "netspout-phase12-cross-domain",
        })
        self.assertEqual({item["kind"] for item in packs.values()}, {
        "AGENTIC_AI",
        "SOFTWARE_SUPPLY_CHAIN",
        "CROSS_DOMAIN",
        })
        self.assertEqual(set(scenarios), {
        "AI-001", "AI-002", "AI-003", "AI-004", "AI-005", "AI-006",
        "SC-001", "SC-002", "SC-003", "SC-004", "SC-005",
        "P12-XD-001", "P12-XD-002",
        })
        self.assertTrue(all(item["replay_policy"]["creates_new_run_id"] for item in scenarios.values()))
        self.assertTrue(all(item["investigation_recipe_ids"] for item in scenarios.values()))
        self.assertTrue(all(item["detection_validation"] for item in scenarios.values()))

    def test_protocol_provenance_and_layer_boundaries_are_explicit(self):
        catalog = NetSpoutCatalog()
        registry = catalog.get_extension_pack_registry()
        phase12_packs = [
            item for item in registry["packs"]
            if item["pack_id"].startswith("netspout-phase12-")
        ]
        evidence = {
            item["evidence_id"]: item
            for pack in phase12_packs
            for item in pack["evidence"]
        }
        self.assertIn("2025-11-25", evidence["EVID-P12-MCP-TOOLS"]["reference"])
        self.assertIn("/v1.0.0/", evidence["EVID-P12-A2A"]["reference"])
        self.assertIn("/v1.1/", evidence["EVID-P12-SLSA"]["reference"])
        for pack in phase12_packs:
            for source in pack["sources"]:
                contract = source["source"]
                self.assertEqual(contract["splunk_contract"]["sourcetypes"][0]["authority"], "NETSPOUT_DEFINED")
                self.assertEqual(contract["splunk_contract"]["cim_mappings"], [])
                self.assertTrue(
                    {"protocol", "audit", "scenario"}
                    <= set(contract["native_contract"]["structural_fields"])
                )

    def test_outcome_semantics_and_protocol_shapes(self):
        cases = [
        ("AI-001", "INCIDENT", "BLOCKED"),
        ("AI-002", "INCIDENT", "DENIED"),
        ("AI-003", "INCIDENT", "CONTAINED"),
        ("AI-005", "INCIDENT", "REJECTED"),
        ("SC-003", "INCIDENT", "VALIDATION_FAILED"),
        ("P12-XD-002", "INCIDENT", "MODELED_DEPLOYMENT"),
        ]
        for scenario_id, phase, expected in cases:
            with self.subTest(scenario_id=scenario_id):
                event = generate_phase12_event(
                    run_id="run-phase12-test",
                    phase=phase,
                    ordinal=2,
                    event_family="ignored",
                    scenario_parameters={"_scenario_id": scenario_id, "_seed": 42},
                )
                payload = json.loads(event.raw)
                self.assertEqual(payload["outcome"], expected)
                self.assertTrue(validate_phase12_event(event.raw))
                if expected in {"BLOCKED", "DENIED", "REJECTED", "VALIDATION_FAILED"}:
                    self.assertFalse(payload["audit"]["downstream_action_executed"])
                if scenario_id == "AI-005":
                    self.assertTrue({"taskId", "contextId", "message", "status"} <= set(payload["protocol"]))
                if scenario_id == "SC-003":
                    self.assertEqual(payload["protocol"]["predicateType"], "https://slsa.dev/provenance/v1")

    def test_state_plan_is_deterministic_and_one_shared_causal_graph(self):
        first = build_phase12_state_plan("run-12", "AI-006", 99)
        replay = build_phase12_state_plan("run-12", "AI-006", 99)
        changed = build_phase12_state_plan("run-12", "AI-006", 100)
        self.assertEqual(first, replay)
        self.assertNotEqual(first.correlation_id, changed.correlation_id)
        self.assertTrue({item["source_entity_id"] for item in first.relationships} <= {item["entity_id"] for item in first.entities})
        self.assertLess(first.timestamp_ns("BASELINE"), first.timestamp_ns("INCIDENT"))

    def test_runtime_fails_closed_for_external_secret_or_executable_inputs(self):
        cases = [
        {"endpoint": "https://external.invalid/mcp"},
        {"access_token": "synthetic-but-disallowed"},
        {"policy_mode": "$(touch /tmp/not-allowed)"},
        {"repository": "git://external.invalid/untrusted"},
        ]
        for parameters in cases:
            with self.subTest(parameters=parameters):
                with self.assertRaises(ValueError):
                    generate_phase12_event(
                        run_id="run-fail-closed",
                        phase="INCIDENT",
                        ordinal=1,
                        event_family="ignored",
                        scenario_parameters={"_scenario_id": "AI-002", **parameters},
                    )

    def test_validator_rejects_denied_action_reported_as_executed(self):
        event = generate_phase12_event(
            run_id="run-denial",
            phase="INCIDENT",
            ordinal=1,
            event_family="ignored",
            scenario_parameters={"_scenario_id": "AI-002"},
        )
        payload = json.loads(event.raw)
        payload["audit"]["downstream_action_executed"] = True
        self.assertFalse(validate_phase12_event(json.dumps(payload)))

    def test_dashboard_recipe_families_integrate_without_regression(self):
        catalog = NetSpoutCatalog()
        dashboard = catalog.get_dashboard_catalog()
        recipe_ids = {item["recipe_id"] for item in dashboard["recipes"]}
        self.assertEqual(len(dashboard["recipes"]), 30)
        self.assertTrue({
        "dashboard-agent-activity",
        "dashboard-mcp-tool-interactions",
        "dashboard-a2a-task-delegation",
        "dashboard-agent-identity-authorization",
        "dashboard-prompt-injection-investigation",
        "dashboard-policy-decision-timeline",
        "dashboard-repository-activity",
        "dashboard-ci-workflow-changes",
        "dashboard-dependency-risk",
        "dashboard-artifact-provenance",
        "dashboard-phase12-causal-correlation",
        } <= recipe_ids)
        self.assertEqual(dashboard["eligible_count"], 27)

    def test_scenario_studio_clone_modify_save_reload_and_fail_closed(self):
        generation = UnifiedGenerationService()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        studio = ScenarioStudioService(
            generation_service=generation,
            storage_dir=temporary.name,
        )
        clone = studio.clone_scenario("AI-002")
        self.assertTrue({item.entity_type for item in clone.entities} >= {
        "agent-or-automation",
        "authorization-policy",
        })
        self.assertEqual({item.parameter_id for item in clone.parameters}, {
        "intensity",
        "policy_mode",
        })
        clone.parameters[0].default = 2
        saved = studio.save_pack(clone)
        reloaded = ScenarioStudioService(
            generation_service=UnifiedGenerationService(),
            storage_dir=temporary.name,
        ).get_pack(saved.pack_id)
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.parameters[0].default, 2)

        unsafe = clone.model_copy(deep=True)
        unsafe.entities[0].attributes["endpoint"] = "https://external.invalid/mcp"
        report = studio.validate_pack(unsafe)
        self.assertFalse(report.valid)
        self.assertTrue(any(item.check_id == "execution-containment" and item.state == "FAIL" for item in report.checks))

    def test_all_sources_have_allow_listed_generator_and_validator(self):
        generation = UnifiedGenerationService()
        self.assertEqual(len(SOURCE_CONFIG), 3)
        for config in SOURCE_CONFIG.values():
            self.assertIn(config["generator"], generation._generator_adapters)
            self.assertIn(config["validator"], generation._validator_adapters)


if __name__ == "__main__":
    unittest.main()
