"""Focused Phase 8C multi-domain contracts and runtime regression tests."""

import os
from pathlib import Path
import sys
import unittest
import uuid
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.cisco_scenario_factory import CiscoScenarioFactoryService
from netspout_core.models import TelemetryTransportConfig
from netspout_core.native_runtime import (
    ChannelRunResult,
    ComponentHealth,
    Evidence,
    HealthState,
    NativeChannel,
    NativeRuntimeFacade,
    PHASES,
    PreflightResult,
)
from netspout_core.unified_generation import (
    GenerationMode,
    UnifiedGenerationRequest,
    UnifiedGenerationService,
)
import netspout_core.unified_generation as unified_generation_module


REFERENCE_IDS = (
    "C100-ENT-001",
    "C100-DC-001",
    "C100-SEC-001",
    "C100-CRI-002",
)


class RecordingSyslogRuntime:
    def __init__(self, config, dispatcher=None):
        self.dispatcher = dispatcher
        self.base = NativeRuntimeFacade(config, dispatcher=dispatcher)
        self.calls = []

    def capabilities(self):
        return self.base.capabilities()

    def health(self):
        return self.base.health()

    def preflight(self, channels=None):
        components = [
            ComponentHealth(
                "phase8c-{}".format(channel.value.lower()),
                HealthState.READY,
                "focused test receiver",
                channel,
            )
            for channel in channels or ()
        ]
        return PreflightResult(ready=True, components=components)

    def run_syslog(
        self,
        run_id,
        scenario_id,
        entity_id,
        seed,
        payload,
        *,
        phase="BASELINE",
        sourcetype="netspout:rfc5424",
    ):
        self.calls.append(
            {
                "run_id": run_id,
                "scenario_id": scenario_id,
                "entity_id": entity_id,
                "phase": phase,
                "sourcetype": sourcetype,
                "raw": payload,
            }
        )
        return ChannelRunResult(
            channel=NativeChannel.SYSLOG,
            run_id=run_id,
            scenario_id=scenario_id,
            entity_id=entity_id,
            seed=seed,
            phases=(phase,),
            evidence=[
                Evidence("GENERATED", True, "generated", 1),
                Evidence("UDP_SENT", True, "sent", 1),
                Evidence("RECEIVER_OBSERVED", True, "received", 1),
                Evidence("NORMALIZED", True, "normalized", 1),
                Evidence("SPLUNK_DISPATCHED", True, "dispatched", 1),
                Evidence("SPLUNK_OBSERVED", True, "observed", 1),
            ],
            success=True,
            source_transport="Syslog/UDP",
            destination_transport="HEC",
            raw_artifacts={"raw": payload},
        )


class RuntimeFactory:
    def __init__(self):
        self.instances = []

    def __call__(self, config, dispatcher=None):
        instance = RecordingSyslogRuntime(config, dispatcher)
        self.instances.append(instance)
        return instance


class TestPhase8CMultiDomainValidation(unittest.TestCase):
    def setUp(self):
        self.catalog = NetSpoutCatalog(str(REPO_ROOT / "catalog"))
        self.runtime_factory = RuntimeFactory()
        self.service = UnifiedGenerationService(
            catalog=self.catalog,
            native_runtime_factory=self.runtime_factory,
        )
        self.transport = TelemetryTransportConfig(
            hec_enabled=True,
            hec_url="https://splunk.example.invalid:8088/services/collector",
            hec_token=uuid.uuid4().hex,
            hec_index="idx_network_ops",
        )

    def _run(self, scenario_id):
        with patch.object(
            self.service, "_check_hec", return_value=(True, "HTTP 200")
        ), patch.object(
            self.service,
            "_check_splunk_search",
            return_value=(True, "authenticated"),
        ):
            return self.service.run(
                UnifiedGenerationRequest(
                    mode=GenerationMode.SCENARIO,
                    selection_id=scenario_id,
                    transport_id="transport-local-hec",
                    destination_id="destination-local-docker-splunk",
                    scenario_parameters={"seed": 73},
                ),
                self.transport,
            )

    def test_one_truthful_reference_is_exposed_per_domain(self):
        factory = CiscoScenarioFactoryService(
            REPO_ROOT / "catalog" / "cisco_100_scenarios.json"
        )
        references = [
            factory._by_id["C100-ENT-001"],
            factory._by_id["C100-SP-001"],
            factory._by_id["C100-DC-001"],
            factory._by_id["C100-SEC-001"],
            factory._by_id["C100-CRI-002"],
        ]
        self.assertEqual(len({item.domain for item in references}), 5)
        for item in references:
            self.assertEqual(item.maturity.value, "GOLDEN")
            self.assertTrue(item.execution_enabled)
            self.assertTrue(item.evidence_references)
            self.assertTrue(item.source_contracts)
            self.assertTrue(item.runtime_validation)
            self.assertTrue(item.splunk_validation)
        for scenario_id in REFERENCE_IDS:
            decision = factory.execution_decision(scenario_id)
            self.assertEqual(decision["runtime_scenario_id"], scenario_id)
            self.assertEqual(
                decision["delegation"], "GUIDED_SCENARIO_EXPERIENCE"
            )

    def test_phase_structures_are_exact_and_vendor_bounded(self):
        cases = (
            (
                "template-cisco-ios-xe-link-updown",
                "FAILOVER",
                "%LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down",
            ),
            (
                "template-cisco-nx-os-link-lifecycle",
                "FAILOVER",
                "%ETHPORT-5-IF_DOWN_LINK_FAILURE: Interface Ethernet1/31 is down (Link failure)",
            ),
            (
                "template-cisco-nx-os-link-lifecycle",
                "RECOVERY",
                "%ETHPORT-5-IF_UP: Interface Ethernet1/31 is up in Layer3",
            ),
            (
                "template-cisco-asa-connection-lifecycle",
                "RECOVERY",
                "%ASA-6-302014: Teardown TCP connection",
            ),
        )
        for profile_id, phase, expected in cases:
            interface_id = {
                "template-cisco-ios-xe-link-updown": "GigabitEthernet0/1",
                "template-cisco-nx-os-link-lifecycle": "Ethernet1/31",
                "template-cisco-asa-connection-lifecycle": "outside",
            }[profile_id]
            raw = self.service._render_declarative_payload(
                profile_id,
                phase=phase,
                ordinal=0,
                seed=73,
                entity_id="reserved-test-device",
                interface_id=interface_id,
            )
            profile = self.service._declarative_profile(profile_id)
            self.assertIn(expected, raw)
            self.assertTrue(
                self.service._validate_declarative_payload(profile, raw, phase)
            )
        asa = self.service._render_declarative_payload(
            "template-cisco-asa-connection-lifecycle",
            phase="FAILOVER",
            ordinal=0,
            seed=73,
            entity_id="asa-edge01",
            interface_id="outside",
        )
        self.assertIn("192.0.2.80", asa)
        self.assertIn("198.51.100.25", asa)

    def test_all_new_references_use_one_generic_lifecycle_path(self):
        expected_counts = {
            "C100-ENT-001": 4,
            "C100-DC-001": 4,
            "C100-SEC-001": 11,
            "C100-CRI-002": 8,
        }
        real_builder = unified_generation_module.build_shared_enterprise_state_plan
        with patch.object(
            unified_generation_module,
            "build_shared_enterprise_state_plan",
            wraps=real_builder,
        ) as build_plan:
            for scenario_id in REFERENCE_IDS:
                run = self._run(scenario_id)
                calls = self.runtime_factory.instances[-1].calls
                self.assertEqual(run.status, "COMPLETED")
                self.assertEqual(len(calls), expected_counts[scenario_id])
                self.assertEqual(
                    {item["phase"] for item in calls}, set(PHASES)
                )
                self.assertEqual(
                    sum(
                        len(item.raw_artifact_digests)
                        for item in run.channel_results
                    ),
                    expected_counts[scenario_id],
                )
                self.assertTrue(
                    all(item["scenario_id"] == scenario_id for item in calls)
                )
        self.assertEqual(build_plan.call_count, len(REFERENCE_IDS))

    def test_cross_domain_sources_share_run_and_clock_but_keep_identities(self):
        run = self._run("C100-CRI-002")
        calls = self.runtime_factory.instances[-1].calls
        self.assertEqual(len({item["run_id"] for item in calls}), 1)
        self.assertEqual(
            {item["entity_id"] for item in calls},
            {"catalyst-9600-operations01", "cisco-asr9k-pe1"},
        )
        for phase in PHASES:
            self.assertEqual(
                {item["sourcetype"] for item in calls if item["phase"] == phase},
                {
                    "netspout:cisco:iosxe:syslog",
                    "netspout:cisco:iosxr:syslog",
                },
            )
        self.assertEqual(len(run.channel_results), 2)

    def test_pack_owned_sources_use_source_scoped_splunk_searches(self):
        with patch.object(
            self.service, "_execute_splunk_search", return_value=(1, None)
        ) as search:
            count, error = self.service._search_splunk_for_source(
                "test-run",
                "cisco-nx-os-interface-syslog",
                self.transport,
            )
        self.assertEqual((count, error), (1, None))
        self.assertIn(
            'sourcetype="netspout:cisco:nxos:syslog"',
            search.call_args.args[0],
        )

    def test_core_runtime_has_no_phase8c_scenario_or_vendor_branch(self):
        source = (
            REPO_ROOT / "src" / "netspout_core" / "unified_generation.py"
        ).read_text(encoding="utf-8")
        for scenario_id in REFERENCE_IDS:
            self.assertNotIn(scenario_id, source)
        for vendor_marker in ("%LINK-3-UPDOWN", "%ETHPORT-", "%ASA-"):
            self.assertNotIn(vendor_marker, source)


if __name__ == "__main__":
    unittest.main()
