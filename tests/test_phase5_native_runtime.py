"""Focused contract tests for the canonical Phase 5 native runtime facade."""

import os
import sys
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import TelemetryTransportConfig
from netspout_core.native_runtime import (
    build_shared_enterprise_state_plan,
    CapabilityLevel,
    ChannelRunResult,
    Evidence,
    HealthState,
    NativeChannel,
    NativeRuntimeFacade,
    PHASES,
)
from netspout_core.snmp_agent import SimulatedSnmpAgent


class FakeDispatcher:
    def __init__(self, accepted=True):
        self.accepted = accepted
        self.logs = []

    def dispatch_log(self, log, config):
        self.logs.append((log, config))
        return {"hec": {"success": self.accepted, "message": "mock response"}}

    def emit_otel(self, payload, endpoint, headers=None):
        return self.accepted, "mock OTLP response"


class FakeCollector:
    def __init__(self, before=None, after=None, recent=None, forwarded=0):
        self.snapshots = iter([
            before or {"packets_total": 0, "records_total": 0},
            after or {"packets_total": 0, "records_total": 0},
        ])
        self.recent = list(recent or [])
        self.health_snapshots = iter([0, forwarded])

    def get_prometheus_metrics(self):
        return next(self.snapshots)

    def get_recent_flows(self):
        return self.recent

    def get_detailed_health(self):
        return SimpleNamespace(
            state=SimpleNamespace(value="RECEIVING"),
            flows_forwarded_total=next(self.health_snapshots),
        )

    def run_preflight_check(self):
        return {"overall_ready": False}

    def register_correlation(
        self, observation_domain_id, run_id, scenario_id, entity_id, phase
    ):
        return {
            "registered": True,
            "observation_domain_id": observation_domain_id,
            "boundary": "COLLECTOR_NORMALIZED",
        }


class FakeFlowTransport:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def send_batch(self, records, session, force_template=False):
        return SimpleNamespace(
            records_encoded=len(records),
            datagrams_sent=1,
            errors=[],
            protocol=self.kwargs["protocol"],
        )


class TestPhase5NativeRuntime(unittest.TestCase):
    def setUp(self):
        runtime_token = uuid.uuid4().hex
        runtime_password = uuid.uuid4().hex
        self.config = TelemetryTransportConfig(
            hec_enabled=True,
            hec_url="https://splunk.example.invalid:8088/services/collector",
            hec_token=runtime_token,
            hec_index="idx_network_ops",
            hec_metric_index="cisco_mdt_metrics",
            hec_ssl_verify=True,
            hec_allow_insecure_tls=False,
            otel_enabled=True,
            otel_endpoint="https://otel.example.invalid",
            native_flow_enabled=True,
            native_flow_collector_host="127.0.0.1",
            native_flow_netflow_port=2055,
            native_flow_ipfix_port=4739,
        )
        self.environment = {
            "NETSPOUT_REST_SEARCH_URL": "https://splunk.example.invalid:8089/services/search/jobs/export",
            "NETSPOUT_SPLUNK_USER": "runtime-user",
            "NETSPOUT_SPLUNK_PASSWORD": runtime_password,
        }

    def test_capabilities_are_typed_and_otel_remains_partial(self):
        facade = NativeRuntimeFacade(self.config, self.environment)
        capabilities = facade.capabilities()
        self.assertEqual(set(capabilities), set(NativeChannel))
        self.assertEqual(capabilities[NativeChannel.OTEL].level, CapabilityLevel.PARTIAL)
        self.assertIn("COLLECTOR_OBSERVED", capabilities[NativeChannel.IPFIX].evidence_stages)
        self.assertNotEqual(
            capabilities[NativeChannel.SYSLOG].source_transport,
            capabilities[NativeChannel.SYSLOG].destination_transport,
        )

    def test_health_does_not_promote_imports_or_configuration_to_healthy(self):
        facade = NativeRuntimeFacade(self.config, self.environment)
        health = facade.health()
        self.assertNotIn("HEALTHY", {item.state.value for item in health})
        self.assertEqual(
            next(item for item in health if item.component == "snmp_receiver").state,
            HealthState.READY,
        )
        self.assertEqual(
            next(item for item in health if item.component == "destination").state,
            HealthState.DEGRADED,
        )

    def test_syslog_preserves_raw_wire_payload_then_adds_correlation(self):
        dispatcher = FakeDispatcher()
        facade = NativeRuntimeFacade(self.config, self.environment, dispatcher=dispatcher)
        raw = "<165>1 2026-10-06T10:00:00Z pe1 bgp 7 ID47 - neighbor down"
        result = facade.run_syslog("run-5", "service_provider_cisco", "cisco-asr9k-pe1", 42, raw)

        stages = {item.stage: item.proven for item in result.evidence}
        self.assertTrue(stages["RECEIVER_OBSERVED"])
        self.assertTrue(stages["SPLUNK_DISPATCHED"])
        self.assertFalse(stages["SPLUNK_OBSERVED"])
        self.assertEqual(result.raw_artifacts["wire_payload"], raw)
        self.assertEqual(result.raw_artifacts["receiver_observation"]["raw"], raw)
        normalized = dispatcher.logs[0][0]
        self.assertEqual(normalized.raw_log, raw)
        self.assertEqual(normalized.netspout_run_id, "run-5")

    def test_udp_send_is_never_promoted_to_flow_receipt(self):
        collector = FakeCollector()
        facade = NativeRuntimeFacade(
            self.config,
            self.environment,
            collector_factory=lambda **_: collector,
            flow_transport_factory=FakeFlowTransport,
        )
        result = facade.run_flow(
            NativeChannel.IPFIX,
            "run-no-receipt",
            "service_provider_cisco",
            "cisco-asr9k-pe1",
            42,
        )
        stages = {item.stage: item.proven for item in result.evidence}
        self.assertTrue(stages["UDP_SENT"])
        self.assertFalse(stages["COLLECTOR_OBSERVED"])
        self.assertFalse(stages["DECODED"])
        self.assertFalse(result.success)

    def test_flow_receipt_requires_independent_collector_evidence(self):
        collector = FakeCollector(
            before={"packets_total": 10, "records_total": 20},
            after={"packets_total": 11, "records_total": 21},
            forwarded=1,
        )
        facade = NativeRuntimeFacade(
            self.config,
            self.environment,
            collector_factory=lambda **_: collector,
            flow_transport_factory=FakeFlowTransport,
        )
        result = facade.run_flow(
            NativeChannel.NETFLOW_V9,
            "run-observed",
            "service_provider_cisco",
            "cisco-asr9k-pe1",
            7,
        )
        stages = {item.stage: item.proven for item in result.evidence}
        self.assertTrue(stages["COLLECTOR_OBSERVED"])
        self.assertTrue(stages["DECODED"])
        self.assertTrue(stages["FORWARDED"])
        self.assertFalse(stages["SPLUNK_OBSERVED"])

    def test_flow_send_failure_is_reported_without_later_stage_promotion(self):
        class FailedTransport(FakeFlowTransport):
            def send_batch(self, records, session, force_template=False):
                return SimpleNamespace(
                    records_encoded=len(records),
                    datagrams_sent=0,
                    errors=["socket failure"],
                )

        facade = NativeRuntimeFacade(
            self.config,
            self.environment,
            collector_factory=lambda **_: FakeCollector(),
            flow_transport_factory=FailedTransport,
        )
        result = facade.run_flow(
            NativeChannel.IPFIX,
            "run-failed",
            "service_provider_cisco",
            "cisco-asr9k-pe1",
            42,
        )
        stages = {item.stage: item.proven for item in result.evidence}
        self.assertFalse(stages["UDP_SENT"])
        self.assertFalse(stages["COLLECTOR_OBSERVED"])
        self.assertIn("socket failure", result.errors)

    def test_otel_acceptance_is_not_observation_or_full_success(self):
        facade = NativeRuntimeFacade(
            self.config,
            self.environment,
            dispatcher=FakeDispatcher(accepted=True),
        )
        result = facade.run_otel("run-otel", "service_provider_cisco", "pe1", 42, {"resourceLogs": []})
        stages = {item.stage: item.proven for item in result.evidence}
        self.assertTrue(stages["DESTINATION_ACCEPTED"])
        self.assertFalse(stages["DESTINATION_OBSERVED"])
        self.assertFalse(result.success)

    def test_correlated_run_fails_closed_without_shared_state_plan(self):
        facade = NativeRuntimeFacade(self.config, self.environment)
        with self.assertRaisesRegex(
            ValueError, "explicit shared enterprise state plan"
        ), patch.object(facade, "run_snmp") as snmp, patch.object(
            facade, "run_gnmi"
        ) as gnmi:
            facade.run_correlated("shared-run", 99)
        snmp.assert_not_called()
        gnmi.assert_not_called()

    def test_shared_plan_has_ordered_coherent_recovery(self):
        plan = build_shared_enterprise_state_plan(
            "shared-run",
            "test-correlated-interface-degradation",
            "cisco-asr9k-pe1",
            99,
        )
        self.assertEqual(plan.phases, PHASES)
        self.assertEqual(plan.interface_id, "HundredGigE0/0/0/1")
        self.assertEqual(plan.snmp_wire_interface_id, plan.interface_id)
        timestamps = [plan.timestamp_ns(phase) for phase in plan.phases]
        self.assertEqual(timestamps, sorted(timestamps))
        self.assertEqual(
            [
                snapshot.interfaces[plan.interface_id].oper_status
                for snapshot in plan.snapshots
            ],
            ["UP", "DOWN", "DOWN", "UP"],
        )

    def test_snmp_agent_consumes_shared_store_with_matching_wire_identity(self):
        plan = build_shared_enterprise_state_plan(
            "shared-run",
            "test-correlated-interface-degradation",
            "cisco-asr9k-pe1",
            99,
        )
        agent = SimulatedSnmpAgent(
            bind_port=0,
            state_store=plan.state_store,
            seed=99,
            device_id=plan.entity_id,
        )
        self.assertIs(agent.state_store, plan.state_store)
        plan.activate("DEGRADE")
        agent.set_phase("DEGRADE")
        self.assertEqual(
            agent.oid_store.get_exact(
                "1.3.6.1.2.1.2.2.1.8.1"
            ).value,
            2,
        )
        self.assertEqual(
            agent.oid_store.get_exact(
                "1.3.6.1.2.1.2.2.1.2.1"
            ).value,
            plan.snmp_wire_interface_id,
        )

    def test_correlated_state_mismatch_fails_channel(self):
        facade = NativeRuntimeFacade(self.config, self.environment)
        plan = build_shared_enterprise_state_plan(
            "shared-run",
            "test-correlated-interface-degradation",
            "cisco-asr9k-pe1",
            99,
        )

        def result(channel, *_args):
            trace = [
                {
                    "phase": snapshot.phase,
                    "timestamp_ns": plan.timestamp_ns(snapshot.phase),
                    "entity_id": plan.entity_id,
                    "interface_id": plan.interface_id,
                    "native_interface_id": (
                        plan.snmp_wire_interface_id
                        if channel == NativeChannel.SNMP
                        else plan.interface_id
                    ),
                    "if_index": plan.snmp_if_index,
                    "oper_status": snapshot.interfaces[
                        plan.interface_id
                    ].oper_status,
                }
                for snapshot in plan.snapshots
            ]
            if channel == NativeChannel.GNMI:
                trace[-1]["oper_status"] = "DOWN"
            receiver_stage = (
                "RECEIVER_OBSERVED"
                if channel == NativeChannel.SNMP
                else "COLLECTOR_RECEIVED"
            )
            return ChannelRunResult(
                channel=channel,
                run_id="shared-run",
                scenario_id="test-correlated-interface-degradation",
                entity_id=plan.entity_id,
                seed=99,
                phases=PHASES,
                evidence=[
                    Evidence("GENERATED", True, "generated", 1),
                    Evidence(receiver_stage, True, "received", 1),
                    Evidence("SPLUNK_DISPATCHED", True, "dispatched", 1),
                    Evidence("VALIDATED", False, "legacy validator", 0),
                ],
                success=False,
                source_transport="native",
                destination_transport="HEC",
                raw_artifacts={
                    "shared_state_store": plan.state_store,
                    "shared_simulation_clock": plan.clock,
                    "correlated_state_trace": trace,
                },
            )

        with patch.object(
            facade,
            "run_snmp",
            side_effect=lambda *args: result(NativeChannel.SNMP),
        ), patch.object(
            facade,
            "run_gnmi",
            side_effect=lambda *args: result(NativeChannel.GNMI),
        ):
            correlated = facade.run_correlated(
                "shared-run",
                99,
                scenario_id="test-correlated-interface-degradation",
                entity_id=plan.entity_id,
                state_plan=plan,
            )
        self.assertFalse(correlated.correlated)
        self.assertTrue(correlated.channels[NativeChannel.SNMP].success)
        self.assertTrue(
            next(
                item
                for item in correlated.channels[NativeChannel.SNMP].evidence
                if item.stage == "VALIDATED"
            ).proven
        )
        self.assertFalse(correlated.channels[NativeChannel.GNMI].success)
        self.assertIn(
            "RECOVERY oper_status",
            " ".join(correlated.channels[NativeChannel.GNMI].errors),
        )

    def test_missing_runtime_search_credentials_fails_closed(self):
        facade = NativeRuntimeFacade(self.config, runtime_environment={})
        result = facade.run_snmp("run", "service_provider_cisco", "pe1", 42)
        self.assertFalse(result.success)
        self.assertIn("Missing runtime destination configuration", result.errors[0])


if __name__ == "__main__":
    unittest.main()
