"""Canonical Phase 5 native telemetry runtime facade.

This module deliberately separates protocol/source transport from destination
transport and reports only evidence that was observed at each boundary.
"""

from __future__ import annotations

import os
import base64
import json
import socket
import ssl
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from netspout_core.collector_evidence import CollectorEvidenceAdapter
from netspout_core.embedded_pipelines import EmbeddedSyslogServer
from netspout_core.exporter_session import ExporterSession
from netspout_core.models import FlowRecord, LogEntry, TelemetryTransportConfig
from netspout_core.telemetry_dispatcher import TelemetryDispatcher
from netspout_core.transport_native_flow import NativeFlowTransport
from netspout_core.gnmi.state_store import (
    CANONICAL_PHASES,
    DeviceStateSnapshot,
    ScenarioStateStore,
    normalize_phase,
)


PHASES: Tuple[str, ...] = ("BASELINE", "DEGRADE", "FAILOVER", "RECOVERY")


@dataclass(frozen=True)
class SimulationClock:
    """Immutable phase clock shared by every channel in one correlated run."""

    phase_timestamps_ns: Tuple[Tuple[str, int], ...]

    def timestamp_ns(self, phase: str) -> int:
        normalized = normalize_phase(phase)
        return dict(self.phase_timestamps_ns)[normalized]


@dataclass
class SharedEnterpriseStatePlan:
    """One explicit enterprise store and clock for a bounded native run."""

    state_store: ScenarioStateStore
    clock: SimulationClock
    entity_id: str
    interface_id: str
    snapshots: Tuple[DeviceStateSnapshot, ...]
    snmp_if_index: int = 1
    snmp_wire_interface_id: str = "HundredGigE0/0/0/1"

    @property
    def phases(self) -> Tuple[str, ...]:
        return tuple(snapshot.phase for snapshot in self.snapshots)

    def snapshot(self, phase: str) -> DeviceStateSnapshot:
        normalized = normalize_phase(phase)
        return next(item for item in self.snapshots if item.phase == normalized)

    def activate(self, phase: str) -> DeviceStateSnapshot:
        snapshot = self.snapshot(phase)
        self.state_store.set_position(snapshot.phase, snapshot.tick)
        return snapshot

    def timestamp_ns(self, phase: str) -> int:
        return self.clock.timestamp_ns(phase)

    def timestamp_seconds(self, phase: str) -> float:
        return self.timestamp_ns(phase) / 1_000_000_000.0


def build_shared_enterprise_state_plan(
    run_id: str,
    scenario_id: str,
    entity_id: str,
    seed: int,
    interface_id: str = "HundredGigE0/0/0/1",
) -> SharedEnterpriseStatePlan:
    store = ScenarioStateStore(
        run_id=run_id,
        scenario_id=scenario_id,
        seed=seed,
        initial_phase=PHASES[0],
    )
    snapshots = tuple(
        store.get_snapshot(entity_id, phase=phase, tick=index)
        for index, phase in enumerate(PHASES)
    )
    if any(interface_id not in snapshot.interfaces for snapshot in snapshots):
        raise RuntimeConfigurationError(
            f"shared interface {interface_id!r} is absent from {entity_id!r}"
        )
    timestamps = tuple((item.phase, item.timestamp_ns) for item in snapshots)
    if tuple(timestamp for _, timestamp in timestamps) != tuple(
        sorted(timestamp for _, timestamp in timestamps)
    ):
        raise RuntimeConfigurationError("shared simulation clock is not ordered")
    return SharedEnterpriseStatePlan(
        state_store=store,
        clock=SimulationClock(timestamps),
        entity_id=entity_id,
        interface_id=interface_id,
        snapshots=snapshots,
    )


class NativeChannel(str, Enum):
    SYSLOG = "SYSLOG"
    SNMP = "SNMP"
    GNMI = "GNMI"
    NETFLOW_V9 = "NETFLOW_V9"
    IPFIX = "IPFIX"
    OTEL = "OTEL"


class CapabilityLevel(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"


class HealthState(str, Enum):
    RUNNING = "RUNNING"
    REACHABLE = "REACHABLE"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass(frozen=True)
class ChannelCapability:
    channel: NativeChannel
    level: CapabilityLevel
    source_transport: str
    destination_transport: str
    evidence_stages: Tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class ComponentHealth:
    component: str
    state: HealthState
    detail: str
    channel: Optional[NativeChannel] = None


@dataclass(frozen=True)
class Evidence:
    stage: str
    proven: bool
    detail: str
    count: int = 0


@dataclass
class PreflightResult:
    ready: bool
    components: List[ComponentHealth]


@dataclass
class ChannelRunResult:
    channel: NativeChannel
    run_id: str
    scenario_id: str
    entity_id: str
    seed: int
    phases: Tuple[str, ...]
    evidence: List[Evidence]
    success: bool
    source_transport: str
    destination_transport: str
    raw_artifacts: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def highest_proven_stage(self) -> str:
        proven = [item.stage for item in self.evidence if item.proven]
        return proven[-1] if proven else "NONE"


@dataclass
class CorrelatedRunResult:
    run_id: str
    scenario_id: str
    entity_id: str
    seed: int
    phases: Tuple[str, ...]
    channels: Dict[NativeChannel, ChannelRunResult]
    state_plan: SharedEnterpriseStatePlan

    @property
    def correlated(self) -> bool:
        return bool(self.channels) and all(
            result.success
            and result.run_id == self.run_id
            and result.scenario_id == self.scenario_id
            and result.entity_id == self.entity_id
            and result.seed == self.seed
            and result.phases == self.phases
            for result in self.channels.values()
        )


class RuntimeConfigurationError(ValueError):
    """Raised when an external destination is missing runtime configuration."""


def _as_mapping(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    if hasattr(value, "model_dump"):
        return dict(value.model_dump(mode="json"))
    if hasattr(value, "dict"):
        return dict(value.dict())
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return dict(vars(value))


def _count(value: Any, name: str) -> int:
    raw = getattr(value, name, 0)
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


class NativeRuntimeFacade:
    """Typed facade over the existing native protocol implementations."""

    def __init__(
        self,
        transport_config: TelemetryTransportConfig,
        runtime_environment: Optional[Mapping[str, str]] = None,
        *,
        dispatcher: Optional[TelemetryDispatcher] = None,
        syslog_server_factory: Callable[..., EmbeddedSyslogServer] = EmbeddedSyslogServer,
        collector_factory: Callable[..., CollectorEvidenceAdapter] = CollectorEvidenceAdapter,
        flow_transport_factory: Callable[..., NativeFlowTransport] = NativeFlowTransport,
        snmp_orchestrator_factory: Optional[Callable[..., Any]] = None,
        gnmi_orchestrator_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.transport_config = transport_config
        self.environment = dict(os.environ if runtime_environment is None else runtime_environment)
        self.dispatcher = dispatcher or TelemetryDispatcher()
        self._syslog_server_factory = syslog_server_factory
        self._collector_factory = collector_factory
        self._flow_transport_factory = flow_transport_factory
        self._snmp_orchestrator_factory = snmp_orchestrator_factory
        self._gnmi_orchestrator_factory = gnmi_orchestrator_factory
        self._active_syslog_server: Optional[EmbeddedSyslogServer] = None

    def capabilities(self) -> Dict[NativeChannel, ChannelCapability]:
        return {
            NativeChannel.SYSLOG: ChannelCapability(
                NativeChannel.SYSLOG,
                CapabilityLevel.SUPPORTED,
                "RFC5424/3164 UDP -> EmbeddedSyslogServer",
                "TelemetryDispatcher -> configured destination",
                (
                    "GENERATED",
                    "UDP_SENT",
                    "RECEIVER_OBSERVED",
                    "NORMALIZED",
                    "SPLUNK_DISPATCHED",
                    "SPLUNK_OBSERVED",
                ),
                "UDP_SENT alone never proves receiver observation.",
            ),
            NativeChannel.SNMP: ChannelCapability(
                NativeChannel.SNMP,
                CapabilityLevel.SUPPORTED,
                "native SNMPv2c -> bundled receiver/poller",
                "SnmpSplunkBridge -> configured HEC/search destination",
                ("GENERATED", "ENCODED", "SENT", "ACKNOWLEDGED", "RECEIVER_OBSERVED", "SPLUNK_DISPATCHED", "SPLUNK_OBSERVED", "VALIDATED"),
            ),
            NativeChannel.GNMI: ChannelCapability(
                NativeChannel.GNMI,
                CapabilityLevel.SUPPORTED,
                "native gNMI gRPC target -> bundled subscriber",
                "GnmiSplunkBridge -> configured HEC/search destination",
                ("GENERATED", "SERVER_PUBLISHED", "COLLECTOR_RECEIVED", "NORMALIZED", "SPLUNK_DISPATCHED", "SPLUNK_OBSERVED", "VALIDATED"),
            ),
            NativeChannel.NETFLOW_V9: self._flow_capability(NativeChannel.NETFLOW_V9),
            NativeChannel.IPFIX: self._flow_capability(NativeChannel.IPFIX),
            NativeChannel.OTEL: ChannelCapability(
                NativeChannel.OTEL,
                CapabilityLevel.PARTIAL,
                "OTLP/HTTP sender",
                "configured OTLP endpoint",
                ("GENERATED", "DESTINATION_ACCEPTED", "DESTINATION_OBSERVED"),
                "Acceptance remains PARTIAL until independent destination observation is proved.",
            ),
        }

    @staticmethod
    def _flow_capability(channel: NativeChannel) -> ChannelCapability:
        return ChannelCapability(
            channel,
            CapabilityLevel.SUPPORTED,
            f"{channel.value} binary UDP via NativeFlowTransport",
            "GoFlow2 collector -> forwarder -> configured HEC destination",
            ("GENERATED", "ENCODED", "UDP_SENT", "COLLECTOR_OBSERVED", "DECODED", "FORWARDED", "SPLUNK_OBSERVED"),
            "UDP_SENT alone never proves collector receipt.",
        )

    def health(self) -> List[ComponentHealth]:
        config = self.transport_config
        destination = (
            ComponentHealth("destination", HealthState.DEGRADED, "Destination is configured but has not been reached.")
            if bool(config.hec_enabled and config.hec_url and config.hec_token)
            else ComponentHealth("destination", HealthState.NOT_CONFIGURED, "HEC URL/token not configured.")
        )
        receiver_probes = {
            item.channel: item
            for item in self.preflight(
                [NativeChannel.SYSLOG, NativeChannel.SNMP, NativeChannel.GNMI]
            ).components
            if item.channel is not None
        }
        flow_state = HealthState.NOT_CONFIGURED
        flow_detail = "Native flow collection is disabled."
        flow_configured = bool(
            config.native_flow_enabled
            or self.environment.get("NETSPOUT_GOFLOW_METRICS_URL")
        )
        if flow_configured:
            try:
                raw_health = self._collector_adapter().get_detailed_health()
                state_value = (
                    getattr(raw_health, "state", "")
                    or _as_mapping(raw_health).get("state", "")
                )
                raw_state = str(
                    getattr(state_value, "value", state_value)
                ).upper()
                flow_state = (
                    HealthState.READY
                    if raw_state in {"READY", "RUNNING", "HEALTHY", "RECEIVING"}
                    else HealthState.DEGRADED
                )
                flow_detail = (
                    "Collector health probe reported ready."
                    if flow_state is HealthState.READY
                    else "Collector health probe did not report ready."
                )
            except Exception as exc:
                flow_state = HealthState.FAILED
                flow_detail = "Collector health probe failed: {}".format(
                    type(exc).__name__
                )
        return [
            ComponentHealth(
                "syslog_receiver",
                receiver_probes[NativeChannel.SYSLOG].state,
                receiver_probes[NativeChannel.SYSLOG].detail,
                NativeChannel.SYSLOG,
            ),
            ComponentHealth(
                "snmp_receiver",
                receiver_probes[NativeChannel.SNMP].state,
                receiver_probes[NativeChannel.SNMP].detail,
                NativeChannel.SNMP,
            ),
            ComponentHealth(
                "gnmi_subscriber",
                receiver_probes[NativeChannel.GNMI].state,
                receiver_probes[NativeChannel.GNMI].detail,
                NativeChannel.GNMI,
            ),
            ComponentHealth("netflow_v9_runtime", flow_state, flow_detail, NativeChannel.NETFLOW_V9),
            ComponentHealth("ipfix_runtime", flow_state, flow_detail, NativeChannel.IPFIX),
            ComponentHealth("otel_runtime", HealthState.NOT_CONFIGURED if not config.otel_enabled else HealthState.DEGRADED, "Independent OTLP observation is not configured/proved.", NativeChannel.OTEL),
            destination,
        ]

    def preflight(self, channels: Optional[Iterable[NativeChannel]] = None) -> PreflightResult:
        requested = tuple(channels or NativeChannel)
        checks: List[ComponentHealth] = []
        if NativeChannel.SYSLOG in requested:
            server = self._syslog_server_factory(host="127.0.0.1", port=0)
            try:
                started = bool(server.start())
                checks.append(
                    ComponentHealth(
                        "bundled-syslog-receiver",
                        HealthState.READY if started else HealthState.FAILED,
                        "Receiver started and bound an ephemeral UDP socket."
                        if started
                        else "Receiver failed to start.",
                        NativeChannel.SYSLOG,
                    )
                )
            except Exception as exc:
                checks.append(
                    ComponentHealth(
                        "bundled-syslog-receiver",
                        HealthState.FAILED,
                        "Receiver start check failed: {}".format(type(exc).__name__),
                        NativeChannel.SYSLOG,
                    )
                )
            finally:
                server.stop()
        if NativeChannel.SNMP in requested:
            receiver = None
            try:
                from netspout_core.transport_native_snmp import LoopbackSnmpTestReceiver

                receiver = LoopbackSnmpTestReceiver(
                    expected_community=self.transport_config.native_snmp_community
                )
                ready = bool(receiver.start() and receiver._running)
                checks.append(ComponentHealth(
                    "bundled-snmp-receiver",
                    HealthState.READY if ready else HealthState.FAILED,
                    "Receiver started and bound an ephemeral UDP socket."
                    if ready else "Receiver failed to bind.",
                    NativeChannel.SNMP,
                ))
            except Exception as exc:
                checks.append(ComponentHealth(
                    "bundled-snmp-receiver",
                    HealthState.FAILED,
                    "Receiver start check failed: {}".format(type(exc).__name__),
                    NativeChannel.SNMP,
                ))
            finally:
                if receiver is not None:
                    receiver.stop()
        if NativeChannel.GNMI in requested:
            server = None
            try:
                from netspout_core.gnmi.collector_pipeline import InternalGrpcGnmiCollector
                from netspout_core.gnmi.server import NativeGnmiServer, NativeGnmiServerConfig

                server = NativeGnmiServer(
                    NativeGnmiServerConfig(bind_address="127.0.0.1", bind_port=0)
                )
                port = server.start()
                collector = InternalGrpcGnmiCollector(
                    host="127.0.0.1", port=port, timeout_sec=2.0
                )
                probe = collector.collect_once(
                    target="node-cisco8k",
                    paths=["/system/state"],
                    run_id="preflight-" + uuid.uuid4().hex,
                    scenario_id="openconfig_mdt_streaming",
                )
                ready = bool(probe.ledger.collector_received)
                checks.append(ComponentHealth(
                    "bundled-gnmi-subscriber",
                    HealthState.READY if ready else HealthState.FAILED,
                    "Server and bundled subscriber completed a loopback RPC."
                    if ready else "Bundled subscriber did not observe a loopback RPC.",
                    NativeChannel.GNMI,
                ))
            except Exception as exc:
                checks.append(ComponentHealth(
                    "bundled-gnmi-subscriber",
                    HealthState.FAILED,
                    "Subscriber loopback check failed: {}".format(type(exc).__name__),
                    NativeChannel.GNMI,
                ))
            finally:
                if server is not None:
                    server.stop()
        if any(c in (NativeChannel.NETFLOW_V9, NativeChannel.IPFIX) for c in requested):
            try:
                raw = self._collector_adapter().run_preflight_check()
                ready = bool(raw.get("overall_ready"))
                for channel in requested:
                    if channel not in (NativeChannel.NETFLOW_V9, NativeChannel.IPFIX):
                        continue
                    checks.append(ComponentHealth(
                        "bundled-{}-collector".format(channel.value.lower().replace("_", "-")),
                        HealthState.READY if ready else HealthState.DEGRADED,
                        "Collector and forwarder probes passed." if ready else "Collector or forwarder probe failed.",
                        channel,
                    ))
            except Exception as exc:
                for channel in requested:
                    if channel in (NativeChannel.NETFLOW_V9, NativeChannel.IPFIX):
                        checks.append(ComponentHealth(
                            "bundled-{}-collector".format(channel.value.lower().replace("_", "-")),
                            HealthState.FAILED,
                            "Collector readiness check failed: {}".format(type(exc).__name__),
                            channel,
                        ))
        if NativeChannel.OTEL in requested:
            checks.append(ComponentHealth(
                "otel_destination",
                HealthState.DEGRADED if self.transport_config.otel_enabled else HealthState.NOT_CONFIGURED,
                "OTLP endpoint configured but independent observation is unproved." if self.transport_config.otel_enabled else "OTLP endpoint disabled.",
                NativeChannel.OTEL,
            ))
        ready = bool(checks) and all(item.state in (HealthState.READY, HealthState.REACHABLE, HealthState.RUNNING) for item in checks)
        return PreflightResult(ready=ready, components=checks)

    def _destination_credentials(self) -> Dict[str, str]:
        cfg = self.transport_config
        values = {
            "hec_url": str(cfg.hec_url or ""),
            "hec_token": str(cfg.hec_token or ""),
            "rest_search_url": self.environment.get("NETSPOUT_REST_SEARCH_URL") or self.environment.get("NETSPOUT_REST_URL", ""),
            "rest_username": self.environment.get("NETSPOUT_SPLUNK_USER", ""),
            "rest_password": self.environment.get("NETSPOUT_SPLUNK_PASSWORD", ""),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise RuntimeConfigurationError(
                "Missing runtime destination configuration: " + ", ".join(missing)
            )
        return values

    def _build_snmp_orchestrator(
        self,
        seed: int,
        entity_id: str,
        scenario_id: str,
        state_plan: Optional[SharedEnterpriseStatePlan] = None,
    ) -> Any:
        from netspout_core.snmp_splunk_e2e import SnmpSplunkBridge, SnmpSplunkE2EOrchestrator

        credentials = self._destination_credentials()
        bridge = SnmpSplunkBridge(
            **credentials,
            index=self.transport_config.hec_index,
        )
        factory = self._snmp_orchestrator_factory or SnmpSplunkE2EOrchestrator
        kwargs = {
            "index": self.transport_config.hec_index,
            "device_id": entity_id,
            "seed": seed,
            "splunk_bridge": bridge,
        }
        if state_plan is not None:
            kwargs["state_plan"] = state_plan
        orchestrator = factory(**kwargs)
        # The existing standards-backed PDU fixtures are reused, while
        # correlation metadata reflects the selected Phase 5 scenario.
        orchestrator.scenario_id = scenario_id
        return orchestrator

    def _build_gnmi_orchestrator(
        self, state_plan: Optional[SharedEnterpriseStatePlan] = None
    ) -> Any:
        from netspout_core.gnmi.splunk_e2e import GnmiSplunkBridge, GnmiSplunkE2EOrchestrator

        credentials = self._destination_credentials()
        bridge = GnmiSplunkBridge(
            hec_url=credentials["hec_url"],
            hec_token=credentials["hec_token"],
            rest_search_url=credentials["rest_search_url"],
            rest_username=credentials["rest_username"],
            rest_password=credentials["rest_password"],
            event_index=self.transport_config.hec_index,
            metric_index=self.transport_config.hec_metric_index,
        )
        factory = self._gnmi_orchestrator_factory or GnmiSplunkE2EOrchestrator
        kwargs = {
            "event_index": self.transport_config.hec_index,
            "metric_index": self.transport_config.hec_metric_index,
            "splunk_bridge": bridge,
        }
        if state_plan is not None:
            kwargs["state_plan"] = state_plan
        return factory(**kwargs)

    def _collector_adapter(self) -> CollectorEvidenceAdapter:
        host = self.environment.get(
            "NETSPOUT_COLLECTOR_HOST",
            self.transport_config.native_flow_collector_host,
        )
        metrics_url = self.environment.get(
            "NETSPOUT_GOFLOW_METRICS_URL",
            f"http://{host}:8080/metrics",
        )
        forwarder_url = self.environment.get(
            "NETSPOUT_FLOW_FORWARDER_STATUS_URL",
            f"http://{host}:8082",
        )
        hec_base = str(self.transport_config.hec_url or "").rstrip("/")
        if hec_base.endswith("/event"):
            hec_base = hec_base[:-6]
        splunk_health_url = self.environment.get(
            "NETSPOUT_HEC_HEALTH_URL",
            f"{hec_base}/health",
        )
        return self._collector_factory(
            goflow_metrics_url=metrics_url,
            forwarder_status_url=forwarder_url,
            splunk_hec_url=splunk_health_url,
        )

    def run_snmp(
        self,
        run_id: str,
        scenario_id: str,
        entity_id: str,
        seed: int,
        state_plan: Optional[SharedEnterpriseStatePlan] = None,
    ) -> ChannelRunResult:
        try:
            orchestrator = self._build_snmp_orchestrator(
                seed, entity_id, scenario_id, state_plan
            )
            scorecard, artifacts = orchestrator.execute_e2e_run(run_id=run_id)
            stage_map = getattr(scorecard, "stage_classification", {}) or {}
            stage_counts = {
                "GENERATED": int(getattr(scorecard, "generated_notifications", 0)),
                "ENCODED": int(getattr(scorecard, "encoded_notifications", 0)),
                "SENT": int(getattr(scorecard, "sent_notifications", 0)),
                "ACKNOWLEDGED": int(getattr(scorecard, "informs_acknowledged", 0)),
                "RECEIVER_OBSERVED": (
                    int(getattr(scorecard, "receiver_observed_notifications", 0))
                    + int(getattr(scorecard, "polling_responses", 0))
                ),
                "SPLUNK_DISPATCHED": int(
                    getattr(scorecard, "splunk_dispatched_records", 0)
                ),
                "SPLUNK_OBSERVED": int(
                    getattr(scorecard, "splunk_observed_records", 0)
                ),
                "VALIDATED": int(
                    getattr(scorecard, "splunk_observed_records", 0)
                ),
            }
            evidence = [
                Evidence(
                    stage,
                    str(stage_map.get(stage, "NO")).upper()
                    in ("YES", "PASS", "PROVEN"),
                    f"SNMP scorecard stage {stage}.",
                    stage_counts[stage],
                )
                for stage in self.capabilities()[NativeChannel.SNMP].evidence_stages
            ]
            return self._result(NativeChannel.SNMP, run_id, scenario_id, entity_id, seed, evidence, artifacts, getattr(scorecard, "validation_result", "") == "PASS")
        except Exception as exc:
            return self._failed_result(NativeChannel.SNMP, run_id, scenario_id, entity_id, seed, exc)

    def run_gnmi(
        self,
        run_id: str,
        scenario_id: str,
        entity_id: str,
        seed: int,
        state_plan: Optional[SharedEnterpriseStatePlan] = None,
    ) -> ChannelRunResult:
        expected_entity = (
            state_plan.entity_id
            if state_plan is not None
            else (
                "cisco-asr9k-pe1"
                if scenario_id == "service_provider_cisco"
                else "node-cisco8k"
            )
        )
        if entity_id != expected_entity:
            return self._failed_result(
                NativeChannel.GNMI,
                run_id,
                scenario_id,
                entity_id,
                seed,
                RuntimeConfigurationError(
                    f"gNMI scenario {scenario_id!r} is modeled for entity {expected_entity!r}, not {entity_id!r}"
                ),
            )
        try:
            orchestrator = self._build_gnmi_orchestrator(state_plan)
            run_kwargs = {
                "scenario_id": scenario_id,
                "run_id": run_id,
                "seed": seed,
            }
            if state_plan is not None:
                run_kwargs["include_stream_modes"] = False
            scorecard, artifacts = orchestrator.run_scenario_e2e(**run_kwargs)
            ledger = getattr(scorecard, "ledger", None)
            names = self.capabilities()[NativeChannel.GNMI].evidence_stages
            attr_names = {
                "GENERATED": "generated",
                "SERVER_PUBLISHED": "server_published",
                "COLLECTOR_RECEIVED": "collector_received",
                "NORMALIZED": "normalized",
                "SPLUNK_DISPATCHED": "splunk_dispatched",
                "SPLUNK_OBSERVED": "splunk_observed",
                "VALIDATED": "validated",
            }
            evidence = [
                Evidence(
                    stage,
                    bool(getattr(ledger, attr_names[stage], False)),
                    f"gNMI ledger stage {stage}.",
                    int(
                        getattr(
                            ledger,
                            attr_names[stage] + "_count",
                            int(bool(getattr(ledger, attr_names[stage], False))),
                        )
                    ),
                )
                for stage in names
            ]
            return self._result(NativeChannel.GNMI, run_id, scenario_id, entity_id, seed, evidence, artifacts, all(item.proven for item in evidence))
        except Exception as exc:
            return self._failed_result(NativeChannel.GNMI, run_id, scenario_id, entity_id, seed, exc)

    def run_syslog(
        self,
        run_id: str,
        scenario_id: str,
        entity_id: str,
        seed: int,
        raw_payload: str,
        *,
        receive_timeout: float = 1.0,
    ) -> ChannelRunResult:
        server = self._syslog_server_factory(host="127.0.0.1", port=0)
        evidence = [Evidence("GENERATED", True, "Caller supplied raw syslog wire payload.", 1)]
        artifacts: Dict[str, Any] = {"wire_payload": raw_payload}
        errors: List[str] = []
        try:
            if not server.start():
                raise RuntimeError("Embedded syslog receiver failed to start.")
            self._active_syslog_server = server
            port = server._udp_sock.getsockname()[1]  # actual ephemeral source receiver port
            wire_bytes = raw_payload.encode("utf-8")
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sent = sock.sendto(wire_bytes, ("127.0.0.1", port))
            evidence.append(Evidence("UDP_SENT", sent == len(wire_bytes), "Local OS accepted the UDP datagram; receipt is not implied.", 1 if sent else 0))

            deadline = time.monotonic() + receive_timeout
            observed: Optional[Dict[str, Any]] = None
            while time.monotonic() < deadline:
                recent = server.get_recent_messages(1)
                if recent:
                    observed = recent[-1]
                    break
                time.sleep(0.01)
            received = observed is not None and observed.get("raw") == raw_payload
            evidence.append(Evidence("RECEIVER_OBSERVED", received, "Embedded receiver captured the exact raw payload." if received else "No matching receiver observation.", 1 if received else 0))
            if not received:
                return self._result(NativeChannel.SYSLOG, run_id, scenario_id, entity_id, seed, evidence, artifacts, False, ["UDP send was not promoted to receipt."])

            artifacts["receiver_observation"] = dict(observed or {})
            log = LogEntry(
                timestamp=str((observed or {}).get("timestamp", time.time())),
                device_id=entity_id,
                src_ip=str((observed or {}).get("source_ip", "127.0.0.1")),
                dest_ip="127.0.0.1",
                protocol="UDP",
                duration="0",
                action="observed",
                signature="native-syslog",
                status="normal",
                raw_log=raw_payload,
                node_type="router",
                node_id=entity_id,
                vendor="cisco",
                sourcetype="netspout:rfc5424",
                netspout_run_id=run_id,
                netspout_scenario_id=scenario_id,
                netspout_phase=PHASES[0],
                netspout_device_id=entity_id,
            )
            evidence.append(Evidence("NORMALIZED", True, "Correlation was added after receiver observation; raw_log is unchanged.", 1))
            dispatch = self.dispatcher.dispatch_log(log, self._hec_destination_config())
            artifacts["destination_result"] = dispatch
            accepted = any(
                isinstance(value, Mapping) and value.get("success") is True
                for value in dispatch.values()
            )
            evidence.extend(
                [
                    Evidence(
                        "SPLUNK_DISPATCHED",
                        accepted,
                        "Configured Splunk destination acknowledged dispatch."
                        if accepted
                        else "Splunk destination did not acknowledge dispatch.",
                        1 if accepted else 0,
                    ),
                    Evidence(
                        "SPLUNK_OBSERVED",
                        False,
                        "Awaiting source-scoped authenticated Splunk search.",
                        0,
                    ),
                ]
            )
            return self._result(NativeChannel.SYSLOG, run_id, scenario_id, entity_id, seed, evidence, artifacts, accepted, errors)
        except Exception as exc:
            errors.append(str(exc))
            return self._result(NativeChannel.SYSLOG, run_id, scenario_id, entity_id, seed, evidence, artifacts, False, errors)
        finally:
            server.stop()
            if self._active_syslog_server is server:
                self._active_syslog_server = None

    def run_flow(
        self,
        channel: NativeChannel,
        run_id: str,
        scenario_id: str,
        entity_id: str,
        seed: int,
        records: Optional[Sequence[FlowRecord]] = None,
    ) -> ChannelRunResult:
        if channel not in (NativeChannel.NETFLOW_V9, NativeChannel.IPFIX):
            raise ValueError("run_flow supports NETFLOW_V9 and IPFIX only")
        cfg = self.transport_config
        collector_host = self.environment.get(
            "NETSPOUT_COLLECTOR_HOST",
            cfg.native_flow_collector_host,
        )
        port = cfg.native_flow_netflow_port if channel is NativeChannel.NETFLOW_V9 else cfg.native_flow_ipfix_port
        collector = self._collector_adapter()
        before = collector.get_prometheus_metrics()
        before_recent = collector.get_recent_flows()
        before_health = collector.get_detailed_health()
        flow_records = list(records or [self._default_flow(run_id, scenario_id, seed)])
        evidence = [Evidence("GENERATED", bool(flow_records), "Deterministic flow records generated.", len(flow_records))]
        try:
            registration = collector.register_correlation(
                cfg.native_flow_observation_domain_id,
                run_id,
                scenario_id,
                entity_id,
                PHASES[0],
            )
            transport = self._flow_transport_factory(
                destination_host=collector_host,
                destination_port=port,
                protocol=channel.value,
                rate_pps=cfg.native_flow_rate_limit_pps,
                max_packets_per_run=cfg.native_flow_packet_cap,
                template_refresh_policy=cfg.native_flow_template_refresh_policy,
                test_mode=False,
            )
            session = ExporterSession(
                node_id=entity_id,
                exporter_ip="127.0.0.1",
                observation_domain_id=cfg.native_flow_observation_domain_id,
                base_time_epoch_ms=seed * 1000,
                template_refresh_policy=cfg.native_flow_template_refresh_policy,
            )
            sent = transport.send_batch(flow_records, session, force_template=True)
            encoded = _count(sent, "records_encoded")
            datagrams = _count(sent, "datagrams_sent")
            evidence.extend([
                Evidence("ENCODED", encoded == len(flow_records), "Native encoder produced protocol packets.", encoded),
                Evidence("UDP_SENT", datagrams > 0, "Local OS accepted UDP datagram(s); collector receipt is not implied.", datagrams),
            ])
            time.sleep(0.2)
            after = collector.get_prometheus_metrics()
            packet_delta = max(0, int(after.get("packets_total", 0)) - int(before.get("packets_total", 0)))
            record_delta = max(0, int(after.get("records_total", 0)) - int(before.get("records_total", 0)))
            recent = collector.get_recent_flows()
            correlated = [
                row for row in recent
                if row.get("netspout_run_id") == run_id
            ]
            new_rows = recent[len(before_recent):] if recent[:len(before_recent)] == before_recent else []
            domain_matches = [
                row for row in new_rows
                if row.get("observation_domain_id") == cfg.native_flow_observation_domain_id
            ]
            matching = correlated or domain_matches
            observed = packet_delta > 0 or bool(matching)
            decoded = record_delta > 0 or bool(matching)
            evidence.extend([
                Evidence("COLLECTOR_OBSERVED", observed, "GoFlow2 metrics/recent-flow evidence increased." if observed else "No independent collector evidence after UDP send.", packet_delta),
                Evidence("DECODED", decoded, "Collector exposed decoded flow evidence." if decoded else "No decoded flow evidence.", record_delta or len(matching)),
            ])
            health = collector.get_detailed_health()
            forwarded_delta = max(
                0,
                _count(health, "flows_forwarded_total")
                - _count(before_health, "flows_forwarded_total"),
            )
            forwarded = forwarded_delta > 0
            observed_count, observation_detail = self._search_flow_observation(run_id)
            evidence.extend([
                Evidence("FORWARDED", forwarded, "Forwarder delivery counter increased." if forwarded else "Forwarder delivery not proved.", forwarded_delta),
                Evidence(
                    "SPLUNK_OBSERVED",
                    observed_count > 0,
                    observation_detail,
                    observed_count,
                ),
            ])
            artifacts = {
                "transport_result": _as_mapping(sent),
                "collector_before": before,
                "collector_after": after,
                "matching_flows": matching,
                "correlation_registration": registration,
            }
            return self._result(
                channel,
                run_id,
                scenario_id,
                entity_id,
                seed,
                evidence,
                artifacts,
                observed and decoded and forwarded,
                list(getattr(sent, "errors", []) or []),
            )
        except Exception as exc:
            return self._result(channel, run_id, scenario_id, entity_id, seed, evidence, {}, False, [str(exc)])

    def _search_flow_observation(self, run_id: str) -> Tuple[int, str]:
        try:
            credentials = self._destination_credentials()
            query = (
                'search index="{}" sourcetype="netflow:collector" '
                'netspout_run_id="{}" | stats count'
            ).format(self.transport_config.hec_index, run_id)
            data = urllib.parse.urlencode(
                {"search": query, "output_mode": "json"}
            ).encode("utf-8")
            auth = base64.b64encode(
                "{}:{}".format(
                    credentials["rest_username"],
                    credentials["rest_password"],
                ).encode("utf-8")
            ).decode("ascii")
            request = urllib.request.Request(
                credentials["rest_search_url"],
                data=data,
                headers={"Authorization": "Basic " + auth},
            )
            context = ssl.create_default_context()
            if not getattr(self.transport_config, "hec_ssl_verify", True):
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(
                request, timeout=5.0, context=context
            ) as response:
                count = 0
                for line in response:
                    payload = json.loads(line.decode("utf-8"))
                    result = payload.get("result", {})
                    if "count" in result:
                        count = int(result["count"])
                return count, (
                    "Authenticated Splunk search proved flow observation."
                    if count
                    else "Authenticated Splunk search returned no matching flow."
                )
        except Exception as exc:
            return 0, "Splunk flow observation failed: {}".format(type(exc).__name__)

    def run_otel(self, run_id: str, scenario_id: str, entity_id: str, seed: int, payload: Mapping[str, Any]) -> ChannelRunResult:
        evidence = [Evidence("GENERATED", True, "OTLP payload supplied.", 1)]
        if not self.transport_config.otel_enabled:
            return self._result(NativeChannel.OTEL, run_id, scenario_id, entity_id, seed, evidence, {}, False, ["OTel is not configured."])
        ok, message = self.dispatcher.emit_otel(
            dict(payload),
            self.transport_config.otel_endpoint,
            headers=self.transport_config.otel_headers,
        )
        evidence.extend([
            Evidence("DESTINATION_ACCEPTED", ok, message, 1 if ok else 0),
            Evidence("DESTINATION_OBSERVED", False, "No independent OTLP backend observation is available.", 0),
        ])
        return self._result(NativeChannel.OTEL, run_id, scenario_id, entity_id, seed, evidence, {"dispatch_message": message}, False)

    def run_correlated(
        self,
        run_id: str,
        seed: int,
        *,
        scenario_id: str = "test-correlated-interface-degradation",
        entity_id: str = "cisco-asr9k-pe1",
        state_plan: Optional[SharedEnterpriseStatePlan] = None,
    ) -> CorrelatedRunResult:
        if state_plan is None:
            raise RuntimeConfigurationError(
                "Correlated native execution requires one explicit shared "
                "enterprise state plan."
            )
        if (
            state_plan.entity_id != entity_id
            or state_plan.state_store.run_id != run_id
            or state_plan.state_store.scenario_id != scenario_id
            or state_plan.state_store.seed != seed
        ):
            raise RuntimeConfigurationError(
                "shared state plan identity does not match the correlated run"
            )

        channels = {
            NativeChannel.SNMP: self.run_snmp(
                run_id, scenario_id, entity_id, seed, state_plan
            ),
            NativeChannel.GNMI: self.run_gnmi(
                run_id, scenario_id, entity_id, seed, state_plan
            ),
        }
        expected = [
            {
                "phase": snapshot.phase,
                "timestamp_ns": state_plan.timestamp_ns(snapshot.phase),
                "entity_id": entity_id,
                "interface_id": state_plan.interface_id,
                "if_index": state_plan.snmp_if_index,
                "oper_status": snapshot.interfaces[
                    state_plan.interface_id
                ].oper_status,
            }
            for snapshot in state_plan.snapshots
        ]
        for channel, result in channels.items():
            artifacts = result.raw_artifacts
            trace = artifacts.get("correlated_state_trace")
            errors: List[str] = list(result.errors)
            if artifacts.get("shared_state_store") is not state_plan.state_store:
                errors.append("native execution did not consume the shared state store")
            if artifacts.get("shared_simulation_clock") is not state_plan.clock:
                errors.append("native execution did not consume the shared simulation clock")
            if not isinstance(trace, list) or len(trace) != len(expected):
                errors.append("native execution returned an incomplete state trace")
            else:
                for observed, planned in zip(trace, expected):
                    for key, value in planned.items():
                        if observed.get(key) != value:
                            errors.append(
                                f"{channel.value} state mismatch for "
                                f"{planned['phase']} {key}: "
                                f"{observed.get(key)!r} != {value!r}"
                            )
                native_ids = {item.get("native_interface_id") for item in trace}
                allowed_ids = (
                    {state_plan.snmp_wire_interface_id}
                    if channel is NativeChannel.SNMP
                    else {state_plan.interface_id}
                )
                if native_ids != allowed_ids:
                    errors.append(
                        f"{channel.value} native interface identity mismatch"
                    )
            required_stages = {
                NativeChannel.SNMP: ("RECEIVER_OBSERVED", "SPLUNK_DISPATCHED"),
                NativeChannel.GNMI: ("COLLECTOR_RECEIVED", "SPLUNK_DISPATCHED"),
            }[channel]
            proven_stages = {item.stage for item in result.evidence if item.proven}
            missing_stages = [
                stage for stage in required_stages if stage not in proven_stages
            ]
            if missing_stages:
                errors.append(
                    "{} correlation pipeline did not prove {}".format(
                        channel.value, ", ".join(missing_stages)
                    )
                )
            if errors:
                result.success = False
                result.errors = errors
            else:
                result.evidence = [
                    (
                        Evidence(
                            "VALIDATED",
                            True,
                            "Shared enterprise state, identity, ordering and "
                            "recovery were consistent across native channels.",
                            len(expected),
                        )
                        if item.stage == "VALIDATED"
                        else item
                    )
                    for item in result.evidence
                ]
                result.success = True

        return CorrelatedRunResult(
            run_id=run_id,
            scenario_id=scenario_id,
            entity_id=entity_id,
            seed=seed,
            phases=PHASES,
            channels=channels,
            state_plan=state_plan,
        )

    @staticmethod
    def _default_flow(run_id: str, scenario_id: str, seed: int) -> FlowRecord:
        return FlowRecord(
            src_ip="192.0.2.10",
            dest_ip="198.51.100.20",
            src_port=40000 + (seed % 1000),
            dest_port=443,
            protocol=6,
            packets_count=10 + (seed % 10),
            bytes_count=1000 + seed,
            start_time_ms=seed * 1000,
            end_time_ms=seed * 1000 + 500,
            netspout_run_id=run_id,
            netspout_scenario_id=scenario_id,
            netspout_phase=PHASES[0],
        )

    @staticmethod
    def _result(
        channel: NativeChannel,
        run_id: str,
        scenario_id: str,
        entity_id: str,
        seed: int,
        evidence: List[Evidence],
        artifacts: Dict[str, Any],
        success: bool,
        errors: Optional[List[str]] = None,
    ) -> ChannelRunResult:
        capability = NativeRuntimeFacade._capability_for(channel)
        return ChannelRunResult(
            channel=channel,
            run_id=run_id,
            scenario_id=scenario_id,
            entity_id=entity_id,
            seed=seed,
            phases=PHASES,
            evidence=evidence,
            success=success,
            source_transport=capability.source_transport,
            destination_transport=capability.destination_transport,
            raw_artifacts=artifacts,
            errors=list(errors or []),
        )

    def _hec_destination_config(self) -> TelemetryTransportConfig:
        """Return a destination-only copy so source syslog is never looped back."""
        updates = {
            "syslog_enabled": False,
            "otel_enabled": False,
            "telegraf_enabled": False,
            "native_flow_enabled": False,
            "native_snmp_enabled": False,
        }
        if hasattr(self.transport_config, "model_copy"):
            return self.transport_config.model_copy(update=updates)
        return self.transport_config.copy(update=updates)

    def _failed_result(self, channel: NativeChannel, run_id: str, scenario_id: str, entity_id: str, seed: int, exc: Exception) -> ChannelRunResult:
        return self._result(channel, run_id, scenario_id, entity_id, seed, [], {}, False, [str(exc)])

    @staticmethod
    def _capability_for(channel: NativeChannel) -> ChannelCapability:
        if channel in (NativeChannel.NETFLOW_V9, NativeChannel.IPFIX):
            return NativeRuntimeFacade._flow_capability(channel)
        # Avoid constructing a facade merely to access static metadata.
        source_destination = {
            NativeChannel.SYSLOG: ("RFC5424/3164 UDP -> EmbeddedSyslogServer", "TelemetryDispatcher -> configured destination"),
            NativeChannel.SNMP: ("native SNMPv2c -> bundled receiver/poller", "SnmpSplunkBridge -> configured HEC/search destination"),
            NativeChannel.GNMI: ("native gNMI gRPC target -> bundled subscriber", "GnmiSplunkBridge -> configured HEC/search destination"),
            NativeChannel.OTEL: ("OTLP/HTTP sender", "configured OTLP endpoint"),
        }
        source, destination = source_destination[channel]
        return ChannelCapability(channel, CapabilityLevel.PARTIAL if channel is NativeChannel.OTEL else CapabilityLevel.SUPPORTED, source, destination, ())


__all__ = [
    "CapabilityLevel",
    "build_shared_enterprise_state_plan",
    "ChannelCapability",
    "ChannelRunResult",
    "ComponentHealth",
    "CorrelatedRunResult",
    "Evidence",
    "HealthState",
    "NativeChannel",
    "NativeRuntimeFacade",
    "PHASES",
    "PreflightResult",
    "RuntimeConfigurationError",
    "SharedEnterpriseStatePlan",
    "SimulationClock",
]
