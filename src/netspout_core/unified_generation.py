"""Catalog-driven orchestration for the Phase 3 unified generation experience."""

import base64
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field, model_validator

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.catalog_contracts import VerificationState
from netspout_core.models import LogEntry, TelemetryTransportConfig
from netspout_core.pack_contracts import (
    CompositionDefinition,
    GuidedScenarioManifest,
    IntegrationRecommendation,
    InvestigationRecipe,
    PackRegistry,
    StrictModel,
)
from netspout_core.telemetry_dispatcher import TelemetryDispatcher


class GenerationMode(str, Enum):
    SCENARIO = "SCENARIO"
    DATA_SOURCE = "DATA_SOURCE"
    SOURCETYPE = "SOURCETYPE"
    SINGLE_EVENT = "SINGLE_EVENT"


class PreflightState(str, Enum):
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    BLOCKED = "BLOCKED"


class EvidenceState(str, Enum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    PROVEN = "PROVEN"
    PENDING = "PENDING"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    FAILED = "FAILED"


class UnifiedGenerationRequest(StrictModel):
    mode: GenerationMode
    selection_id: str
    transport_id: str = "transport-local-hec"
    destination_id: str = "destination-local-docker-splunk"
    count: int = Field(default=6, ge=1, le=100)
    rate_eps: int = Field(default=10, ge=1, le=100)
    duration_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    scenario_parameters: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def enforce_mode_semantics(self):
        if self.mode == GenerationMode.SINGLE_EVENT and self.count != 1:
            raise ValueError("Single Event mode requires count=1")
        return self


class PreflightCheck(StrictModel):
    check_id: str
    label: str
    state: str
    detail: str


class UnifiedPreflightResult(StrictModel):
    state: PreflightState
    checks: List[PreflightCheck]
    source_ids: List[str]
    generator_ids: List[str]
    transport_id: str
    destination_id: str


class EvidenceStageResult(StrictModel):
    stage: str
    state: EvidenceState
    count: int = 0
    detail: str


class GeneratedEvent(StrictModel):
    event_id: str
    source_id: str
    contract_id: str
    provenance: List[str]
    transport_id: str
    sourcetype: str
    sourcetype_authority: str
    phase: str
    raw: str


class UnifiedGenerationRun(StrictModel):
    run_id: str
    mode: GenerationMode
    selection_id: str
    scenario_id: Optional[str] = None
    source_ids: List[str]
    generator_ids: List[str]
    transport_id: str
    destination_id: str
    started_at: str
    completed_at: Optional[str] = None
    current_phase: str
    status: str
    events: List[GeneratedEvent]
    evidence: List[EvidenceStageResult]
    integration_readiness: List[Dict[str, Any]]
    investigations: List[Dict[str, Any]]
    limitations: List[str]


class UnifiedGenerationService:
    """Resolve validated declarations, then invoke only allow-listed adapters."""

    SOURCETYPE = "netspout:rfc5424"
    SOURCE_ID = "ietf-syslog-rfc5424"
    GENERATOR_ID = "generator-rfc5424-modeled"
    VALIDATOR_ID = "validator-rfc5424-structure"
    EVENT_FAMILY_ID = "modeled-link-state"
    SCENARIO_ID = "rfc5424-link-state-lifecycle"

    def __init__(
        self,
        catalog: Optional[NetSpoutCatalog] = None,
        dispatcher: Optional[TelemetryDispatcher] = None,
    ):
        self.catalog = catalog or NetSpoutCatalog()
        self.dispatcher = dispatcher or TelemetryDispatcher()
        self.registry = PackRegistry.model_validate(
            self.catalog.get_extension_pack_registry()
        )
        self.runs: Dict[str, UnifiedGenerationRun] = {}
        self._generator_adapters = {
            self.GENERATOR_ID: self._generate_rfc5424_event,
        }
        self._validator_adapters = {
            self.VALIDATOR_ID: self._validate_rfc5424,
        }

    def capabilities(self) -> Dict[str, Any]:
        resources = self.registry._resources()
        sources = {
            item["source_id"]: item
            for item in self.catalog.list_telemetry_sources()
        }
        evidence = {
            item["evidence_id"]: item for item in self.catalog.list_catalog_evidence()
        }
        integrations = {
            item["integration_id"]: item
            for item in self.catalog.list_splunk_integrations()
        }
        recommendations = {
            item.recommendation_id: self._recommendation_view(
                item, integrations, evidence
            )
            for item in resources["recommendations"]
        }
        investigations = {
            item.recipe_id: item.model_dump(mode="json")
            for item in resources["investigations"]
        }

        bound_ids = {
            item.source_id for item in self.registry.catalog_source_bindings
        }
        source_views = []
        for source_id, source in sources.items():
            runnable = source_id in bound_ids and self._source_is_runnable(source)
            source_views.append(
                {
                    **source,
                    "generation": {
                        "runnable": runnable,
                        "state": "READY" if runnable else self._blocked_state(source),
                        "reason": (
                            "Validated catalog source with an allow-listed generator."
                            if runnable
                            else self._blocked_reason(source)
                        ),
                    },
                }
            )

        scenario_views = []
        compositions = {
            item.scenario_id: item for item in self.registry.compositions
        }
        for scenario in resources["scenarios"]:
            composition = compositions.get(scenario.scenario_id)
            scenario_views.append(
                {
                    **scenario.model_dump(mode="json"),
                    "composition_id": (
                        composition.composition_id if composition else None
                    ),
                    "verification_state": self._scenario_verification(scenario, sources),
                    "maturity": self._scenario_pack_maturity(scenario.scenario_id),
                    "source_count": len(scenario.source_ids),
                    "integration_count": len(
                        scenario.integration_recommendation_ids
                    ),
                    "runnable": composition is not None,
                }
            )

        transports = [
            item.model_dump(mode="json")
            for item in resources["transports"]
            if item.implemented
        ]
        destinations = [
            {
                **item.model_dump(mode="json"),
                "label": "Local Docker Splunk",
                "configured": True,
            }
            for item in resources["destinations"]
        ]
        sourcetypes = []
        for source in source_views:
            for claim in source["splunk_contract"]["sourcetypes"]:
                sourcetypes.append(
                    {
                        **claim,
                        "source_id": source["source_id"],
                        "vendor": source["vendor"],
                        "product": source["product"],
                        "source": source["telemetry_source"],
                        "verification_state": source["verification_state"],
                        "provenance": source["provenance"],
                        "integration_ids": source["splunk_contract"][
                            "integration_ids"
                        ],
                        "cim_mappings": source["splunk_contract"]["cim_mappings"],
                        "runnable": source["generation"]["runnable"],
                        "generation_controls": ["count", "rate_eps", "duration_seconds"],
                    }
                )

        return {
            "schema_version": "1.0.0",
            "workflow": [
                "CHOOSE",
                "PREVIEW",
                "CONFIGURE",
                "RUN",
                "OBSERVE",
                "INVESTIGATE",
            ],
            "modes": [
                {
                    "id": "SCENARIO",
                    "label": "Scenario",
                    "description": "Generate one correlated modeled incident lifecycle.",
                },
                {
                    "id": "DATA_SOURCE",
                    "label": "Data Source",
                    "description": "Generate one catalog source independently.",
                },
                {
                    "id": "SOURCETYPE",
                    "label": "Sourcetype / Event Family",
                    "description": "Generate a supported, authority-labeled sourcetype.",
                },
                {
                    "id": "SINGLE_EVENT",
                    "label": "Single Event",
                    "description": "Generate and send exactly one supported event.",
                },
            ],
            "sources": source_views,
            "scenarios": scenario_views,
            "sourcetypes": sourcetypes,
            "event_families": [
                {
                    "event_family_id": self.EVENT_FAMILY_ID,
                    "label": "Modeled interface link-state event",
                    "source_id": self.SOURCE_ID,
                    "sourcetype": self.SOURCETYPE,
                    "runnable": True,
                    "count": 1,
                }
            ],
            "transports": transports,
            "destinations": destinations,
            "integration_recommendations": list(recommendations.values()),
            "investigations": list(investigations.values()),
            "raw_preview_policy": (
                "Generated preview values are fictional and modeled; structural "
                "fields follow the cited RFC 5424 contract."
            ),
        }

    def preview(self, request: UnifiedGenerationRequest) -> Dict[str, Any]:
        resolved = self._resolve(request)
        run_id = "preview-00000000"
        phases = resolved["phases"]
        preview_events = [
            self._generator_adapters[resolved["generator_ids"][0]](
                run_id=run_id,
                phase=phase,
                ordinal=index,
                event_family=resolved["event_family"],
            )
            for index, phase in enumerate(phases[:3])
        ]
        source = resolved["sources"][0]
        return {
            "mode": request.mode.value,
            "selection_id": request.selection_id,
            "scenario": resolved["scenario"],
            "sources": resolved["sources"],
            "bindings": resolved["bindings"],
            "integration_readiness": resolved["integration_readiness"],
            "investigations": resolved["investigations"],
            "raw_preview": [
                event.model_dump(mode="json") for event in preview_events
            ],
            "preview_notice": (
                "Preview values are fictional modeled values. The event structure "
                "and provenance are identified separately."
            ),
            "native_contract": source["native_contract"],
            "splunk_contract": source["splunk_contract"],
            "netspout_contract": source["netspout_contract"],
            "known_limitations": source["known_limitations"],
        }

    def preflight(
        self,
        request: UnifiedGenerationRequest,
        transport_config: TelemetryTransportConfig,
    ) -> UnifiedPreflightResult:
        resolved = self._resolve(request)
        checks = [
            PreflightCheck(
                check_id="composition",
                label="Composition contract valid",
                state="PASS",
                detail="All source, generator, transport, and destination references validated.",
            ),
            PreflightCheck(
                check_id="source-contracts",
                label="Required source contracts available",
                state="PASS",
                detail=", ".join(resolved["source_ids"]),
            ),
            PreflightCheck(
                check_id="generators",
                label="Generator available",
                state="PASS",
                detail=", ".join(resolved["generator_ids"]),
            ),
        ]
        transport_ok = request.transport_id in {
            item["transport_id"] for item in self.capabilities()["transports"]
        }
        checks.append(
            PreflightCheck(
                check_id="transport",
                label="Transport available",
                state="PASS" if transport_ok else "BLOCK",
                detail=request.transport_id,
            )
        )
        destination_ok = request.destination_id in {
            item["destination_id"] for item in self.capabilities()["destinations"]
        }
        checks.append(
            PreflightCheck(
                check_id="destination",
                label="Destination configured",
                state="PASS" if destination_ok else "BLOCK",
                detail=request.destination_id,
            )
        )
        hec_ok, hec_detail = self._check_hec(transport_config)
        checks.append(
            PreflightCheck(
                check_id="destination-reachable",
                label="Splunk destination reachable",
                state="PASS" if hec_ok else "BLOCK",
                detail=hec_detail,
            )
        )
        for recommendation in resolved["integration_readiness"]:
            requirement = recommendation["requirement"]
            detected = recommendation["detected"]
            checks.append(
                PreflightCheck(
                    check_id="integration-" + recommendation["recommendation_id"],
                    label=recommendation["name"],
                    state=(
                        "PASS"
                        if detected
                        else ("BLOCK" if requirement == "REQUIRED" else "WARN")
                    ),
                    detail="{}; detected={}".format(requirement, detected),
                )
            )
        checks.append(
            PreflightCheck(
                check_id="index",
                label="Index available",
                state="WARN",
                detail="Index existence is verified by the post-run Splunk observation search.",
            )
        )
        if any(item.state == "BLOCK" for item in checks):
            state = PreflightState.BLOCKED
        elif any(item.state == "WARN" for item in checks):
            state = PreflightState.READY_WITH_WARNINGS
        else:
            state = PreflightState.READY
        return UnifiedPreflightResult(
            state=state,
            checks=checks,
            source_ids=resolved["source_ids"],
            generator_ids=resolved["generator_ids"],
            transport_id=request.transport_id,
            destination_id=request.destination_id,
        )

    def run(
        self,
        request: UnifiedGenerationRequest,
        transport_config: TelemetryTransportConfig,
    ) -> UnifiedGenerationRun:
        preflight = self.preflight(request, transport_config)
        if preflight.state == PreflightState.BLOCKED:
            raise ValueError("generation preflight is BLOCKED")
        resolved = self._resolve(request)
        run_id = str(uuid.uuid4())
        started_at = _utc_now()
        events: List[GeneratedEvent] = []
        sent = 0
        generated = 0
        valid = 0
        dispatch_errors: List[str] = []
        phases = resolved["phases"]
        pacing = 1.0 / float(request.rate_eps)

        for index, phase in enumerate(phases):
            event = self._generator_adapters[resolved["generator_ids"][0]](
                run_id=run_id,
                phase=phase,
                ordinal=index,
                event_family=resolved["event_family"],
            )
            generated += 1
            events.append(event)
            if self._validator_adapters[self.VALIDATOR_ID](event.raw):
                valid += 1
            entry = self._to_log_entry(event, run_id, resolved.get("scenario_id"))
            result = self.dispatcher.dispatch_log(entry, transport_config)
            hec_result = result.get("hec")
            if hec_result and hec_result.get("success"):
                sent += 1
            else:
                message = (
                    hec_result.get("message")
                    if isinstance(hec_result, dict)
                    else "HEC dispatch was not attempted"
                )
                dispatch_errors.append(str(message))
            if index < len(phases) - 1 and pacing > 0:
                time.sleep(min(pacing, 0.25))

        evidence = self._initial_evidence(
            generated=generated,
            sent=sent,
            valid=valid,
            dispatch_errors=dispatch_errors,
        )
        status = "COMPLETED" if sent == generated else "DEGRADED"
        run = UnifiedGenerationRun(
            run_id=run_id,
            mode=request.mode,
            selection_id=request.selection_id,
            scenario_id=resolved.get("scenario_id"),
            source_ids=resolved["source_ids"],
            generator_ids=resolved["generator_ids"],
            transport_id=request.transport_id,
            destination_id=request.destination_id,
            started_at=started_at,
            completed_at=_utc_now(),
            current_phase=phases[-1],
            status=status,
            events=events,
            evidence=evidence,
            integration_readiness=resolved["integration_readiness"],
            investigations=resolved["investigations"],
            limitations=[
                "HEC acceptance proves dispatch, not indexed Splunk observation.",
                "Receiver observation is not independently available for this HEC path.",
                "No CIM mapping is claimed for the NetSpout-defined sourcetype.",
            ],
        )
        self.runs[run_id] = run
        return run

    def get_run(self, run_id: str) -> Optional[UnifiedGenerationRun]:
        return self.runs.get(run_id)

    def observe(
        self,
        run_id: str,
        transport_config: TelemetryTransportConfig,
    ) -> UnifiedGenerationRun:
        run = self.runs.get(run_id)
        if not run:
            raise KeyError(run_id)
        observed, detail = self._search_splunk(run_id, transport_config)
        updated = []
        for stage in run.evidence:
            if stage.stage == "SPLUNK_OBSERVED":
                updated.append(
                    EvidenceStageResult(
                        stage=stage.stage,
                        state=(
                            EvidenceState.PROVEN
                            if observed > 0
                            else EvidenceState.PENDING
                        ),
                        count=observed,
                        detail=detail,
                    )
                )
            elif stage.stage in {"SOURCETYPE_VERIFIED", "FIELDS_VERIFIED"}:
                updated.append(
                    EvidenceStageResult(
                        stage=stage.stage,
                        state=(
                            EvidenceState.PROVEN
                            if observed > 0
                            else EvidenceState.PENDING
                        ),
                        count=observed,
                        detail=(
                            "Verified by indexed observation."
                            if observed > 0
                            else "Awaiting indexed observation."
                        ),
                    )
                )
            else:
                updated.append(stage)
        run.evidence = updated
        if observed > 0:
            run.status = "OBSERVED"
        self.runs[run_id] = run
        return run

    def run_investigation(
        self,
        run_id: str,
        recipe_id: str,
        transport_config: TelemetryTransportConfig,
    ) -> Dict[str, Any]:
        run = self.runs.get(run_id)
        if not run:
            raise KeyError(run_id)
        recipe = next(
            (
                item
                for item in run.investigations
                if item["recipe_id"] == recipe_id
            ),
            None,
        )
        if not recipe:
            raise ValueError("investigation recipe is not attached to this run")
        query = recipe["spl"].replace("$run_id$", run_id)
        count, detail = self._execute_splunk_search(query, transport_config)
        return {
            "run_id": run_id,
            "recipe_id": recipe_id,
            "portability": recipe["portability"],
            "query": query,
            "status": "SUCCEEDED" if detail is None else "FAILED",
            "result_count": count,
            "detail": detail or "Splunk returned the investigation result.",
        }

    def _resolve(self, request: UnifiedGenerationRequest) -> Dict[str, Any]:
        capabilities = self.capabilities()
        scenarios = {
            item["scenario_id"]: item for item in capabilities["scenarios"]
        }
        source_by_id = {
            item["source_id"]: item for item in capabilities["sources"]
        }
        compositions = {
            item.scenario_id: item for item in self.registry.compositions
        }
        scenario = None
        composition: Optional[CompositionDefinition] = None
        event_family = self.EVENT_FAMILY_ID

        if request.mode == GenerationMode.SCENARIO:
            scenario = scenarios.get(request.selection_id)
            composition = compositions.get(request.selection_id)
            if not scenario or not composition:
                raise ValueError("scenario is not backed by a validated composition")
            source_ids = scenario["source_ids"]
            phases = [item["stage"] for item in scenario["timeline"]]
            generator_ids = [
                item.generator_id for item in composition.source_bindings
            ]
        elif request.mode == GenerationMode.DATA_SOURCE:
            source = source_by_id.get(request.selection_id)
            if not source:
                raise ValueError("unknown catalog source")
            self._require_runnable_source(source)
            source_ids = [source["source_id"]]
            generator_ids = [self.GENERATOR_ID]
            phases = ["GENERATE"] * self._bounded_count(request)
        elif request.mode == GenerationMode.SOURCETYPE:
            claim = next(
                (
                    item
                    for item in capabilities["sourcetypes"]
                    if item["name"] == request.selection_id
                ),
                None,
            )
            if not claim or not claim["runnable"]:
                raise ValueError("sourcetype is not available for generation")
            source_ids = [claim["source_id"]]
            generator_ids = [self.GENERATOR_ID]
            phases = ["GENERATE"] * self._bounded_count(request)
        else:
            family = next(
                (
                    item
                    for item in capabilities["event_families"]
                    if item["event_family_id"] == request.selection_id
                ),
                None,
            )
            if not family or not family["runnable"]:
                raise ValueError("event family is not available for generation")
            source_ids = [family["source_id"]]
            generator_ids = [self.GENERATOR_ID]
            phases = ["SINGLE_EVENT"]

        if request.transport_id != "transport-local-hec":
            raise ValueError("transport is not supported by this runtime binding")
        if request.destination_id != "destination-local-docker-splunk":
            raise ValueError("destination is not supported by this runtime binding")
        for generator_id in generator_ids:
            if generator_id not in self._generator_adapters:
                raise ValueError("generator is not allow-listed")
        sources = [source_by_id[source_id] for source_id in source_ids]
        for source in sources:
            self._require_runnable_source(source)

        recommendation_ids = (
            scenario["integration_recommendation_ids"]
            if scenario
            else ["recommend-rfc5424-direct-ingestion"]
        )
        recommendation_by_id = {
            item["recommendation_id"]: item
            for item in capabilities["integration_recommendations"]
        }
        investigation_ids = (
            composition.investigation_recipe_ids
            if composition
            else ["investigate-rfc5424-run"]
        )
        investigation_by_id = {
            item["recipe_id"]: item for item in capabilities["investigations"]
        }
        return {
            "scenario_id": scenario["scenario_id"] if scenario else None,
            "scenario": scenario,
            "source_ids": source_ids,
            "sources": sources,
            "generator_ids": generator_ids,
            "phases": phases,
            "event_family": event_family,
            "bindings": (
                [
                    item.model_dump(mode="json")
                    for item in composition.source_bindings
                ]
                if composition
                else [
                    {
                        "source_id": source_ids[0],
                        "generator_id": generator_ids[0],
                        "transport_id": request.transport_id,
                        "destination_id": request.destination_id,
                        "validator_ids": [self.VALIDATOR_ID],
                    }
                ]
            ),
            "integration_readiness": [
                recommendation_by_id[item] for item in recommendation_ids
            ],
            "investigations": [
                investigation_by_id[item] for item in investigation_ids
            ],
        }

    def _recommendation_view(
        self,
        recommendation: IntegrationRecommendation,
        integrations: Dict[str, Dict[str, Any]],
        evidence: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        integration = integrations.get(recommendation.integration_id or "")
        return {
            **recommendation.model_dump(mode="json"),
            "name": integration["name"] if integration else "No integration",
            "publisher": integration["publisher"] if integration else None,
            "support_state": (
                integration["support_state"] if integration else "NOT_REQUIRED"
            ),
            "detected": bool(
                integration
                and integration["integration_id"]
                == "netspout-direct-structured-ingestion"
            ),
            "evidence": [
                evidence[evidence_id]
                for evidence_id in recommendation.evidence_ids
                if evidence_id in evidence
            ],
        }

    def _source_is_runnable(self, source: Dict[str, Any]) -> bool:
        return (
            source["verification_state"]
            not in {
                VerificationState.RESEARCH_REQUIRED.value,
                VerificationState.UNSUPPORTED.value,
            }
            and source["netspout_contract"]["runtime_status"]
            in {"READY", "AVAILABLE"}
            and source["source_id"]
            in {item.source_id for item in self.registry.catalog_source_bindings}
        )

    def _require_runnable_source(self, source: Dict[str, Any]) -> None:
        if not self._source_is_runnable(source):
            raise ValueError(self._blocked_reason(source))

    def _blocked_state(self, source: Dict[str, Any]) -> str:
        if source["verification_state"] == "UNSUPPORTED":
            return "UNSUPPORTED"
        if source["verification_state"] == "RESEARCH_REQUIRED":
            return "RESEARCH_REQUIRED"
        return "NOT_AVAILABLE"

    def _blocked_reason(self, source: Dict[str, Any]) -> str:
        if source["verification_state"] == "UNSUPPORTED":
            return "UNSUPPORTED TELEMETRY"
        if source["verification_state"] == "RESEARCH_REQUIRED":
            return (
                "NetSpout does not have sufficient authoritative evidence to "
                "generate this telemetry faithfully."
            )
        return (
            "No validated Phase 3 generator, transport, and destination "
            "composition is available for this source."
        )

    def _scenario_verification(
        self, scenario: GuidedScenarioManifest, sources: Dict[str, Dict[str, Any]]
    ) -> str:
        states = {
            sources[source_id]["verification_state"]
            for source_id in scenario.source_ids
        }
        if "UNSUPPORTED" in states:
            return "UNSUPPORTED"
        if "RESEARCH_REQUIRED" in states:
            return "RESEARCH_REQUIRED"
        if states == {"VERIFIED"}:
            return "VERIFIED"
        return "PARTIALLY_VERIFIED"

    def _scenario_pack_maturity(self, scenario_id: str) -> str:
        for pack in self.registry.packs:
            if any(item.scenario_id == scenario_id for item in pack.scenarios):
                return pack.maturity.value
        return "PLANNED"

    def _bounded_count(self, request: UnifiedGenerationRequest) -> int:
        if request.duration_seconds:
            return min(request.count, request.duration_seconds * request.rate_eps)
        return request.count

    def _generate_rfc5424_event(
        self, run_id: str, phase: str, ordinal: int, event_family: str
    ) -> GeneratedEvent:
        event_id = str(uuid.uuid4())
        phase_values = {
            "BASELINE": ("up", "normal", 0),
            "PRECURSOR": ("up", "degraded", 7),
            "INCIDENT": ("down", "affected", 100),
            "IMPACT": ("down", "affected", 100),
            "DETECTION": ("down", "detected", 100),
            "RECOVERY": ("up", "recovered", 0),
            "GENERATE": ("up", "normal", ordinal % 4),
            "SINGLE_EVENT": ("down", "modeled", 100),
        }
        interface_state, runtime_state, loss_pct = phase_values.get(
            phase, ("up", "normal", 0)
        )
        timestamp = _utc_now()
        raw = (
            '<134>1 {timestamp} edge-router.example.invalid netspout 4242 '
            'LINK_STATE [netspout@32473 run_id="{run_id}" event_id="{event_id}" '
            'phase="{phase}" modeled="true"] interface=GigabitEthernet1/0/1 '
            'state={interface_state} runtime_state={runtime_state} loss_pct={loss_pct}'
        ).format(
            timestamp=timestamp,
            run_id=run_id,
            event_id=event_id,
            phase=phase,
            interface_state=interface_state,
            runtime_state=runtime_state,
            loss_pct=loss_pct,
        )
        return GeneratedEvent(
            event_id=event_id,
            source_id=self.SOURCE_ID,
            contract_id="native-ietf-syslog-rfc5424",
            provenance=["STANDARD_DOCUMENTED", "MODELED_PAYLOAD"],
            transport_id="transport-local-hec",
            sourcetype=self.SOURCETYPE,
            sourcetype_authority="NETSPOUT_DEFINED",
            phase=phase,
            raw=raw,
        )

    def _validate_rfc5424(self, raw: str) -> bool:
        pattern = (
            r"^<\d{1,3}>1 \S+ \S+ \S+ \S+ \S+ "
            r"\[netspout@32473 [^\]]+\] .+$"
        )
        return bool(re.match(pattern, raw))

    def _to_log_entry(
        self, event: GeneratedEvent, run_id: str, scenario_id: Optional[str]
    ) -> LogEntry:
        return LogEntry(
            id=event.event_id,
            timestamp=_utc_now(),
            device_id="edge-router.example.invalid",
            src_ip="192.0.2.10",
            dest_ip="192.0.2.20",
            protocol="SYSLOG",
            duration="0ms",
            signature="NETSPOUT_MODELED_LINK_STATE",
            node_type="router",
            node_id="edge-router",
            vendor="IETF",
            sourcetype=event.sourcetype,
            raw_log=event.raw,
            status="degraded" if event.phase in {"PRECURSOR", "INCIDENT", "IMPACT"} else "normal",
            action="modeled",
            netspout_run_id=run_id,
            netspout_scenario_id=scenario_id,
            netspout_phase=event.phase,
            netspout_device_id="edge-router",
            netspout_event_id=event.event_id,
            netspout_ground_truth="modeled",
        )

    def _initial_evidence(
        self, generated: int, sent: int, valid: int, dispatch_errors: List[str]
    ) -> List[EvidenceStageResult]:
        sent_state = EvidenceState.PROVEN if sent == generated else EvidenceState.FAILED
        return [
            EvidenceStageResult(
                stage="GENERATED",
                state=EvidenceState.PROVEN,
                count=generated,
                detail="Events created by the allow-listed modeled generator.",
            ),
            EvidenceStageResult(
                stage="ENCODED_PUBLISHED",
                state=EvidenceState.PROVEN,
                count=generated,
                detail="RFC 5424 structural validation completed before dispatch.",
            ),
            EvidenceStageResult(
                stage="SENT",
                state=sent_state,
                count=sent,
                detail=(
                    "HEC accepted every dispatch request."
                    if sent == generated
                    else "; ".join(dispatch_errors)
                ),
            ),
            EvidenceStageResult(
                stage="RECEIVER_OBSERVED",
                state=EvidenceState.NOT_AVAILABLE,
                count=0,
                detail="No independent HEC receiver observation adapter is configured.",
            ),
            EvidenceStageResult(
                stage="NORMALIZED",
                state=EvidenceState.NOT_AVAILABLE,
                count=0,
                detail="No CIM mapping is claimed for this NetSpout-defined sourcetype.",
            ),
            EvidenceStageResult(
                stage="SPLUNK_DISPATCHED",
                state=sent_state,
                count=sent,
                detail="This stage records HEC HTTP acceptance, not indexing.",
            ),
            EvidenceStageResult(
                stage="SPLUNK_OBSERVED",
                state=EvidenceState.PENDING,
                count=0,
                detail="Run the authenticated observation search after indexing delay.",
            ),
            EvidenceStageResult(
                stage="SOURCETYPE_VERIFIED",
                state=EvidenceState.PENDING,
                count=0,
                detail="Awaiting indexed observation of the NetSpout-defined sourcetype.",
            ),
            EvidenceStageResult(
                stage="FIELDS_VERIFIED",
                state=EvidenceState.PENDING,
                count=0,
                detail="Awaiting indexed observation of run and phase fields.",
            ),
            EvidenceStageResult(
                stage="VALIDATED",
                state=(
                    EvidenceState.PROVEN
                    if valid == generated
                    else EvidenceState.FAILED
                ),
                count=valid,
                detail="Local validation covers RFC 5424 structure only.",
            ),
        ]

    def _check_hec(
        self, transport_config: TelemetryTransportConfig
    ) -> Tuple[bool, str]:
        if not transport_config.hec_enabled:
            return False, "HEC is disabled in the configured destination."
        if not transport_config.hec_url or not transport_config.hec_token:
            return False, "The configured destination is missing HEC connection data."
        health_url = transport_config.hec_url.rstrip("/")
        if health_url.endswith("/services/collector"):
            health_url += "/health"
        try:
            context = self._ssl_context(transport_config)
            request = urllib.request.Request(health_url, method="GET")
            with urllib.request.urlopen(request, timeout=3.0, context=context) as response:
                if 200 <= response.status < 300:
                    return True, "HEC health endpoint returned HTTP {}.".format(
                        response.status
                    )
                return False, "HEC health endpoint returned HTTP {}.".format(
                    response.status
                )
        except Exception as exc:
            return False, "HEC health check failed: {}".format(type(exc).__name__)

    def _search_splunk(
        self, run_id: str, transport_config: TelemetryTransportConfig
    ) -> Tuple[int, str]:
        query = (
            'search index="{}" sourcetype="{}" netspout_run_id="{}" '
            "| stats count"
        ).format(transport_config.hec_index, self.SOURCETYPE, run_id)
        count, error = self._execute_splunk_search(query, transport_config)
        if error:
            return 0, "Splunk observation unavailable: {}".format(error)
        if count:
            return count, "Authenticated Splunk search proved indexed observation."
        return 0, "Search succeeded; indexing observation is still pending."

    def _execute_splunk_search(
        self, query: str, transport_config: TelemetryTransportConfig
    ) -> Tuple[int, Optional[str]]:
        password = os.environ.get("NETSPOUT_SPLUNK_PASSWORD") or os.environ.get(
            "SPLUNK_PASSWORD"
        )
        username = os.environ.get("NETSPOUT_SPLUNK_USERNAME", "admin")
        if not password:
            return 0, "authenticated Splunk search is not configured"
        endpoint = os.environ.get("NETSPOUT_SPLUNK_REST_URL")
        if not endpoint:
            endpoint = transport_config.hec_url.replace(
                ":8088", ":8089"
            ).replace("/services/collector", "/services/search/jobs/export")
        auth = base64.b64encode(
            "{}:{}".format(username, password).encode("utf-8")
        ).decode("ascii")
        data = urllib.parse.urlencode(
            {"search": query, "output_mode": "json"}
        ).encode("utf-8")
        request = urllib.request.Request(
            endpoint, data=data, headers={"Authorization": "Basic " + auth}
        )
        try:
            context = self._ssl_context(transport_config)
            with urllib.request.urlopen(
                request, timeout=5.0, context=context
            ) as response:
                count = 0
                for line in response:
                    try:
                        payload = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    result = payload.get("result")
                    if not isinstance(result, dict):
                        continue
                    if "count" in result:
                        count = int(result["count"])
                    else:
                        count += 1
                return count, None
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
            return 0, type(exc).__name__

    def _ssl_context(
        self, transport_config: TelemetryTransportConfig
    ) -> ssl.SSLContext:
        context = ssl.create_default_context()
        ca_file = os.environ.get("NETSPOUT_SPLUNK_CA_FILE")
        if ca_file:
            context.load_verify_locations(cafile=ca_file)
        elif (
            getattr(transport_config, "hec_allow_insecure_tls", False)
            or not getattr(transport_config, "hec_ssl_verify", True)
        ):
            # Preserves the existing local-lab transport policy. Phase 3 does
            # not expose or alter this setting in the generation UI.
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
