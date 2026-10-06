"""Focused Phase 5 integration tests for the unified generation workflow."""

import os
import sys
import unittest
import uuid
from unittest.mock import patch


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import TelemetryTransportConfig
from netspout_core.native_runtime import (
    ChannelRunResult,
    CorrelatedRunResult,
    ComponentHealth,
    Evidence,
    HealthState,
    NativeChannel,
    NativeRuntimeFacade,
    PHASES,
    PreflightResult,
)
from netspout_core.unified_generation import (
    ChannelEvidenceResult,
    EvidenceState,
    GenerationMode,
    PreflightState,
    UnifiedChannelResult,
    UnifiedGenerationRequest,
    UnifiedGenerationService,
)


class FakeDispatcher:
    def dispatch_log(self, entry, transport):
        return {"hec": {"success": True, "message": "accepted"}}


class RecordingRuntime:
    def __init__(self, config, dispatcher=None, degraded=()):
        self.base = NativeRuntimeFacade(config, dispatcher=dispatcher)
        self.calls = []
        self.degraded = set(degraded)

    def capabilities(self):
        return self.base.capabilities()

    def health(self):
        return self.base.health()

    def preflight(self, channels=None):
        components = [
            ComponentHealth(
                "test-" + channel.value.lower(),
                (
                    HealthState.DEGRADED
                    if channel in self.degraded
                    else HealthState.READY
                ),
                "independent test readiness evidence",
                channel,
            )
            for channel in channels or ()
        ]
        return PreflightResult(
            ready=all(item.state == HealthState.READY for item in components),
            components=components,
        )

    def _result(
        self, channel, run_id, scenario_id, entity_id, seed, state_plan=None
    ):
        self.calls.append((channel, run_id, scenario_id, entity_id, seed))
        artifacts = {}
        if state_plan is not None:
            native_interface = (
                state_plan.snmp_wire_interface_id
                if channel == NativeChannel.SNMP
                else state_plan.interface_id
            )
            artifacts = {
                "shared_state_store": state_plan.state_store,
                "shared_simulation_clock": state_plan.clock,
                "correlated_state_trace": [
                    {
                        "phase": snapshot.phase,
                        "timestamp_ns": state_plan.timestamp_ns(snapshot.phase),
                        "entity_id": entity_id,
                        "interface_id": state_plan.interface_id,
                        "native_interface_id": native_interface,
                        "if_index": state_plan.snmp_if_index,
                        "oper_status": snapshot.interfaces[
                            state_plan.interface_id
                        ].oper_status,
                    }
                    for snapshot in state_plan.snapshots
                ],
            }
        return ChannelRunResult(
            channel=channel,
            run_id=run_id,
            scenario_id=scenario_id,
            entity_id=entity_id,
            seed=seed,
            phases=PHASES,
            evidence=[
                Evidence("GENERATED", True, "generated", 1),
                Evidence("RECEIVER_OBSERVED", True, "receiver proved", 1),
                Evidence("SPLUNK_OBSERVED", False, "search pending", 0),
            ],
            success=True,
            source_transport="native",
            destination_transport="HEC",
            raw_artifacts=artifacts,
        )

    def run_syslog(self, run_id, scenario_id, entity_id, seed, payload):
        return self._result(
            NativeChannel.SYSLOG, run_id, scenario_id, entity_id, seed
        )

    def run_snmp(self, run_id, scenario_id, entity_id, seed):
        return self._result(
            NativeChannel.SNMP, run_id, scenario_id, entity_id, seed
        )

    def run_gnmi(self, run_id, scenario_id, entity_id, seed):
        return self._result(
            NativeChannel.GNMI, run_id, scenario_id, entity_id, seed
        )

    def run_flow(self, channel, run_id, scenario_id, entity_id, seed):
        return self._result(channel, run_id, scenario_id, entity_id, seed)

    def run_correlated(
        self, run_id, seed, *, scenario_id, entity_id, state_plan
    ):
        channels = {
            channel: self._result(
                channel,
                run_id,
                scenario_id,
                entity_id,
                seed,
                state_plan,
            )
            for channel in (NativeChannel.SNMP, NativeChannel.GNMI)
        }
        return CorrelatedRunResult(
            run_id=run_id,
            scenario_id=scenario_id,
            entity_id=entity_id,
            seed=seed,
            phases=PHASES,
            channels=channels,
            state_plan=state_plan,
        )


class RuntimeFactory:
    def __init__(self, degraded=()):
        self.degraded = degraded
        self.instances = []

    def __call__(self, config, dispatcher=None):
        runtime = RecordingRuntime(config, dispatcher, self.degraded)
        self.instances.append(runtime)
        return runtime


class TestUnifiedNativeGeneration(unittest.TestCase):
    def setUp(self):
        self.transport = TelemetryTransportConfig(
            hec_enabled=True,
            hec_url="https://splunk.example.invalid:8088/services/collector",
            hec_token=uuid.uuid4().hex,
            hec_index="idx_network_ops",
            native_flow_enabled=True,
        )
        self.request = UnifiedGenerationRequest(
            mode=GenerationMode.SCENARIO,
            selection_id="test-correlated-interface-degradation",
            transport_id="transport-local-hec",
            destination_id="destination-local-docker-splunk",
            count=1,
            scenario_parameters={"seed": 73},
        )

    def _service(self, factory):
        return UnifiedGenerationService(
            dispatcher=FakeDispatcher(),
            native_runtime_factory=factory,
        )

    def test_correlated_composition_is_enabled_for_snmp_and_gnmi_only(self):
        factory = RuntimeFactory()
        service = self._service(factory)
        capabilities = service.capabilities()
        scenario = next(
            item
            for item in capabilities["scenarios"]
            if item["scenario_id"] == self.request.selection_id
        )
        self.assertTrue(scenario["runnable"])
        self.assertIsNone(scenario["blocked_reason"])
        self.assertEqual(
            scenario["source_ids"],
            ["ietf-snmpv2c-ifmib", "openconfig-gnmi-interfaces"],
        )
        self.assertIn(
            self.request.selection_id,
            capabilities["native_runtime"]["scenario_ids"],
        )
        self.assertIn(
            "ietf-netflow-v9",
            capabilities["native_runtime"]["source_ids"],
        )
        with patch.object(service, "_check_hec", return_value=(True, "HTTP 200")), patch.object(
            service,
            "_check_splunk_search",
            return_value=(True, "authenticated"),
        ):
            run = service.run(self.request, self.transport)
        self.assertEqual(
            {item.channel for item in run.channel_results}, {"SNMP", "GNMI"}
        )
        self.assertEqual(
            {call[3] for call in factory.instances[-1].calls},
            {"cisco-asr9k-pe1"},
        )

    def test_stopped_required_collector_blocks_preflight(self):
        service = self._service(RuntimeFactory(degraded=(NativeChannel.IPFIX,)))
        request = UnifiedGenerationRequest(
            mode=GenerationMode.DATA_SOURCE,
            selection_id="ietf-ipfix",
            count=1,
        )
        with patch.object(service, "_check_hec", return_value=(True, "HTTP 200")), patch.object(
            service,
            "_check_splunk_search",
            return_value=(True, "authenticated"),
        ):
            result = service.preflight(request, self.transport)
        self.assertEqual(result.state, PreflightState.BLOCKED)
        self.assertEqual(
            next(
                item
                for item in result.checks
                if item.check_id == "native-ietf-ipfix"
            ).state,
            "BLOCK",
        )

    def test_native_data_source_cardinality_fails_closed(self):
        service = self._service(RuntimeFactory())
        for request in (
            UnifiedGenerationRequest(
                mode=GenerationMode.DATA_SOURCE,
                selection_id="openconfig-gnmi-interfaces",
                count=2,
            ),
            UnifiedGenerationRequest(
                mode=GenerationMode.SOURCETYPE,
                selection_id="openconfig:gnmi:telemetry",
                count=1,
                duration_seconds=1,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "exactly one lifecycle"):
                service.preview(request)

    def test_bad_destination_fails_closed_before_runtime_execution(self):
        service = self._service(RuntimeFactory())
        bad = UnifiedGenerationRequest(
            mode=GenerationMode.DATA_SOURCE,
            selection_id="openconfig-gnmi-interfaces",
            count=1,
            destination_id="destination-not-declared",
        )
        with self.assertRaisesRegex(ValueError, "destination"):
            service.preview(bad)

    def test_native_preview_is_truthful_and_empty(self):
        service = self._service(RuntimeFactory())
        preview = service.preview(
            UnifiedGenerationRequest(
                mode=GenerationMode.DATA_SOURCE,
                selection_id="openconfig-gnmi-interfaces",
                count=1,
            )
        )
        self.assertEqual(preview["raw_preview"], [])
        self.assertIn("not fabricated", preview["preview_notice"])

    def test_native_single_event_is_rejected_without_one_update_adapter(self):
        service = self._service(RuntimeFactory())
        request = UnifiedGenerationRequest(
            mode=GenerationMode.SINGLE_EVENT,
            selection_id="openconfig-gnmi-interfaces",
            count=1,
        )
        with self.assertRaisesRegex(ValueError, "exact one-PDU/update"):
            service.preview(request)

    def test_standalone_gnmi_uses_supported_scenario_mapping(self):
        factory = RuntimeFactory()
        service = self._service(factory)
        request = UnifiedGenerationRequest(
            mode=GenerationMode.DATA_SOURCE,
            selection_id="openconfig-gnmi-interfaces",
            count=1,
        )
        with patch.object(service, "_check_hec", return_value=(True, "HTTP 200")), patch.object(
            service,
            "_check_splunk_search",
            return_value=(True, "authenticated"),
        ):
            service.run(request, self.transport)
        call = factory.instances[-1].calls[0]
        self.assertEqual(call[2:4], ("openconfig_mdt_streaming", "node-cisco8k"))

    def test_standalone_syslog_uses_native_receiver_path(self):
        factory = RuntimeFactory()
        service = self._service(factory)
        request = UnifiedGenerationRequest(
            mode=GenerationMode.DATA_SOURCE,
            selection_id="ietf-syslog-rfc5424",
            count=1,
        )
        with patch.object(service, "_check_hec", return_value=(True, "HTTP 200")), patch.object(
            service,
            "_check_splunk_search",
            return_value=(True, "authenticated"),
        ):
            run = service.run(request, self.transport)
        self.assertEqual(run.channel_results[0].channel, "SYSLOG")
        self.assertEqual(
            run.channel_results[0].source_transport_id,
            "transport-native-syslog-udp",
        )

    def test_standalone_netflow_v9_uses_bundled_collector(self):
        factory = RuntimeFactory()
        service = self._service(factory)
        request = UnifiedGenerationRequest(
            mode=GenerationMode.DATA_SOURCE,
            selection_id="ietf-netflow-v9",
            count=1,
        )
        with patch.object(service, "_check_hec", return_value=(True, "HTTP 200")), patch.object(
            service,
            "_check_splunk_search",
            return_value=(True, "authenticated"),
        ):
            run = service.run(request, self.transport)
        self.assertEqual(run.channel_results[0].channel, "NETFLOW_V9")
        self.assertEqual(
            run.channel_results[0].receiver_component_id,
            "bundled-netflow-v9-collector",
        )

    def test_global_evidence_requires_each_required_channel(self):
        service = self._service(RuntimeFactory())

        def channel(source_id, state):
            return UnifiedChannelResult(
                source_id=source_id,
                channel=source_id,
                required=True,
                runtime_adapter_ref="test",
                source_transport_id="native",
                destination_transport_id="transport-local-hec",
                run_id="run",
                scenario_id="scenario",
                entity_id="entity",
                seed=1,
                clock_state="clock",
                status="COMPLETED",
                evidence=[
                    ChannelEvidenceResult(
                        stage="GENERATED", state=state, count=1, detail="test"
                    )
                ],
            )

        evidence = service._native_global_evidence(
            [
                channel("snmp", EvidenceState.PROVEN),
                channel("gnmi", EvidenceState.FAILED),
            ]
        )
        generated = next(item for item in evidence if item.stage == "GENERATED")
        self.assertEqual(generated.state, EvidenceState.FAILED)
        self.assertNotIn("RECEIVER_OBSERVED", {item.stage for item in evidence})

    def test_source_observation_query_cannot_cross_credit_sourcetypes(self):
        service = self._service(RuntimeFactory())
        queries = []

        def capture(query, _config):
            queries.append(query)
            return 0, None

        with patch.object(service, "_execute_splunk_search", side_effect=capture):
            service._search_splunk_for_source(
                "run-1", "ietf-syslog-rfc5424", self.transport
            )
            service._search_splunk_for_source(
                "run-1", "openconfig-gnmi-interfaces", self.transport
            )
            service._search_splunk_for_source(
                "run-1", "ietf-snmpv2c-ifmib", self.transport
            )
            service._search_splunk_for_source(
                "run-1", "ietf-netflow-v9", self.transport
            )
        self.assertEqual(len(queries), 4)
        self.assertNotEqual(queries[0], queries[1])
        self.assertTrue(all('netspout_run_id="run-1"' in item for item in queries))
        self.assertTrue(all("sourcetype=" in item for item in queries))
        self.assertIn('sourcetype="netspout:gnmi:event"', queries[1])
        self.assertIn('sourcetype="netspout:snmp:*"', queries[2])
        self.assertIn('sourcetype="netflow:collector"', queries[3])


if __name__ == "__main__":
    unittest.main()
