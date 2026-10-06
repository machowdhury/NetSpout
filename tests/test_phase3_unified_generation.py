"""Phase 3 catalog-driven unified generation contract tests."""

import os
import sys
import unittest
from unittest.mock import patch


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import TelemetryTransportConfig
from netspout_core.unified_generation import (
    GenerationMode,
    UnifiedGenerationRequest,
    UnifiedGenerationService,
)


class FakeDispatcher:
    def __init__(self, succeeds=True):
        self.succeeds = succeeds
        self.entries = []

    def dispatch_log(self, entry, transport):
        self.entries.append(entry)
        return {
            "hec": {
                "success": self.succeeds,
                "message": "accepted" if self.succeeds else "rejected",
            }
        }


def request(mode, selection_id, count):
    return UnifiedGenerationRequest(
        mode=mode,
        selection_id=selection_id,
        count=count,
        rate_eps=100,
        transport_id="transport-local-hec",
        destination_id="destination-local-docker-splunk",
    )


class TestPhase3UnifiedGeneration(unittest.TestCase):
    def setUp(self):
        self.dispatcher = FakeDispatcher()
        self.service = UnifiedGenerationService(dispatcher=self.dispatcher)
        self.transport = TelemetryTransportConfig(
            hec_enabled=True,
            hec_url="https://splunk.example.invalid:8088/services/collector",
            hec_token="runtime-test-value",
            hec_index="idx_network_ops",
            hec_ssl_verify=True,
            hec_allow_insecure_tls=False,
        )

    def test_01_capabilities_derive_from_catalog_and_packs(self):
        capabilities = self.service.capabilities()
        self.assertEqual(
            capabilities["workflow"],
            ["CHOOSE", "PREVIEW", "CONFIGURE", "RUN", "OBSERVE", "INVESTIGATE"],
        )
        self.assertEqual(len(capabilities["modes"]), 4)
        runnable = [
            item for item in capabilities["sources"] if item["generation"]["runnable"]
        ]
        self.assertEqual(
            {item["source_id"] for item in runnable},
            {
                "ietf-syslog-rfc5424",
                "ietf-snmpv2c-ifmib",
                "ietf-netflow-v9",
                "ietf-ipfix",
                "openconfig-gnmi-interfaces",
            },
        )
        self.assertEqual(
            {
                item["name"]
                for item in capabilities["sourcetypes"]
                if item["runnable"]
            },
            {"netspout:rfc5424", "openconfig:gnmi:telemetry"},
        )
        self.assertGreaterEqual(len(capabilities["scenarios"]), 1)
        legacy_scenario = next(
            item
            for item in capabilities["scenarios"]
            if item["scenario_id"] == "rfc5424-link-state-lifecycle"
        )
        self.assertEqual(
            legacy_scenario["composition_id"],
            "compose-rfc5424-link-state-local",
        )
        self.assertEqual(
            legacy_scenario["verification_state"],
            "PARTIALLY_VERIFIED",
        )

    def test_02_preview_exposes_three_contracts_and_modeled_raw_event(self):
        preview = self.service.preview(
            request(
                GenerationMode.SCENARIO,
                "rfc5424-link-state-lifecycle",
                6,
            )
        )
        self.assertEqual(
            preview["native_contract"]["contract_id"],
            "native-ietf-syslog-rfc5424",
        )
        self.assertEqual(
            preview["splunk_contract"]["sourcetypes"][0]["authority"],
            "NETSPOUT_DEFINED",
        )
        self.assertEqual(
            preview["netspout_contract"]["schema_classification"],
            "MODELED_PAYLOAD",
        )
        raw = preview["raw_preview"][0]
        self.assertEqual(
            raw["provenance"], ["STANDARD_DOCUMENTED", "MODELED_PAYLOAD"]
        )
        self.assertIn("example.invalid", raw["raw"])
        self.assertIn('modeled="true"', raw["raw"])

    def test_03_preflight_is_runtime_derived_and_secret_free(self):
        with patch.object(
            self.service, "_check_hec", return_value=(True, "HTTP 200")
        ):
            result = self.service.preflight(
                request(
                    GenerationMode.DATA_SOURCE,
                    "ietf-syslog-rfc5424",
                    2,
                ),
                self.transport,
            )
        self.assertEqual(result.state.value, "READY_WITH_WARNINGS")
        self.assertTrue(any(item.check_id == "destination-reachable" for item in result.checks))
        serialized = result.model_dump_json()
        self.assertNotIn("runtime-test-value", serialized)
        self.assertNotIn("hec_token", serialized)

    def test_04_all_four_modes_execute_through_one_service(self):
        cases = [
            (GenerationMode.SCENARIO, "rfc5424-link-state-lifecycle", 6, 6),
            (GenerationMode.DATA_SOURCE, "ietf-syslog-rfc5424", 3, 3),
            (GenerationMode.SOURCETYPE, "netspout:rfc5424", 4, 4),
            (GenerationMode.SINGLE_EVENT, "modeled-link-state", 1, 1),
        ]
        with patch.object(
            self.service, "_check_hec", return_value=(True, "HTTP 200")
        ):
            for mode, selection_id, count, expected in cases:
                run = self.service.run(
                    request(mode, selection_id, count), self.transport
                )
                self.assertEqual(len(run.events), expected)
                self.assertEqual(
                    next(item for item in run.evidence if item.stage == "SENT").count,
                    expected,
                )
        self.assertEqual(len(self.dispatcher.entries), 14)

    def test_05_single_event_is_exactly_one_and_has_no_background_scenario(self):
        with self.assertRaises(ValueError):
            request(GenerationMode.SINGLE_EVENT, "modeled-link-state", 2)
        with patch.object(
            self.service, "_check_hec", return_value=(True, "HTTP 200")
        ):
            run = self.service.run(
                request(GenerationMode.SINGLE_EVENT, "modeled-link-state", 1),
                self.transport,
            )
        self.assertEqual(len(run.events), 1)
        self.assertIsNone(run.scenario_id)
        self.assertEqual(run.events[0].phase, "SINGLE_EVENT")

    def test_06_research_and_unsupported_sources_fail_closed(self):
        for source_id in [
            "windows-security-audit-research",
            "supply-chain-platform-unselected",
        ]:
            with self.assertRaises(ValueError):
                self.service.preview(
                    request(GenerationMode.DATA_SOURCE, source_id, 1)
                )
        capabilities = self.service.capabilities()
        states = {
            item["source_id"]: item["generation"]["state"]
            for item in capabilities["sources"]
        }
        self.assertEqual(
            states["windows-security-audit-research"], "RESEARCH_REQUIRED"
        )
        self.assertEqual(
            states["supply-chain-platform-unselected"], "UNSUPPORTED"
        )

    def test_07_transport_and_destination_are_independent_fail_closed_ids(self):
        bad_transport = request(
            GenerationMode.DATA_SOURCE, "ietf-syslog-rfc5424", 1
        ).model_copy(update={"transport_id": "transport-not-declared"})
        with self.assertRaisesRegex(ValueError, "transport"):
            self.service.preview(bad_transport)

        bad_destination = request(
            GenerationMode.DATA_SOURCE, "ietf-syslog-rfc5424", 1
        ).model_copy(update={"destination_id": "destination-not-declared"})
        with self.assertRaisesRegex(ValueError, "destination"):
            self.service.preview(bad_destination)

    def test_08_evidence_stages_do_not_equate_send_with_observation(self):
        with patch.object(
            self.service, "_check_hec", return_value=(True, "HTTP 200")
        ):
            run = self.service.run(
                request(
                    GenerationMode.DATA_SOURCE,
                    "ietf-syslog-rfc5424",
                    2,
                ),
                self.transport,
            )
        stages = {item.stage: item for item in run.evidence}
        self.assertEqual(stages["SENT"].state.value, "PROVEN")
        self.assertEqual(
            stages["RECEIVER_OBSERVED"].state.value, "NOT_AVAILABLE"
        )
        self.assertEqual(stages["SPLUNK_OBSERVED"].state.value, "PENDING")
        self.assertEqual(stages["NORMALIZED"].state.value, "NOT_AVAILABLE")

    def test_09_authenticated_observation_must_return_results(self):
        with patch.object(
            self.service, "_check_hec", return_value=(True, "HTTP 200")
        ):
            run = self.service.run(
                request(GenerationMode.SINGLE_EVENT, "modeled-link-state", 1),
                self.transport,
            )
        with patch.object(
            self.service, "_execute_splunk_search", return_value=(1, None)
        ):
            observed = self.service.observe(run.run_id, self.transport)
        stages = {item.stage: item for item in observed.evidence}
        self.assertEqual(stages["SPLUNK_OBSERVED"].state.value, "PROVEN")
        self.assertEqual(stages["SPLUNK_OBSERVED"].count, 1)
        self.assertEqual(observed.status, "OBSERVED")

    def test_10_investigation_is_attached_and_classified(self):
        with patch.object(
            self.service, "_check_hec", return_value=(True, "HTTP 200")
        ):
            run = self.service.run(
                request(
                    GenerationMode.SCENARIO,
                    "rfc5424-link-state-lifecycle",
                    6,
                ),
                self.transport,
            )
        recipe = run.investigations[0]
        self.assertEqual(recipe["portability"], "NETSPOUT_SPECIFIC")
        self.assertIn("netspout_run_id", recipe["netspout_only_fields"])
        with patch.object(
            self.service, "_execute_splunk_search", return_value=(6, None)
        ):
            result = self.service.run_investigation(
                run.run_id, recipe["recipe_id"], self.transport
            )
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["result_count"], 6)
        self.assertIn(run.run_id, result["query"])

    def test_11_raw_structure_validator_rejects_unstructured_payload(self):
        self.assertTrue(
            self.service._validate_rfc5424(
                self.service._generate_rfc5424_event(
                    "run", "BASELINE", 0, "modeled-link-state"
                ).raw
            )
        )
        self.assertFalse(self.service._validate_rfc5424("plausible vendor text"))


if __name__ == "__main__":
    unittest.main()
