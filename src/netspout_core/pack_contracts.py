"""Strict declarative contracts for independently testable NetSpout extension packs.

This module defines metadata and composition only. It deliberately does not
import, instantiate, or execute generators, transports, scenarios, or queries.
"""

from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import Field, model_validator

from netspout_core.catalog_contracts import (
    EvidenceReference,
    SplunkIntegration,
    StrictModel,
    TelemetryCatalog,
    TelemetrySource,
    VerificationState,
)


class PackKind(str, Enum):
    VENDOR_PRODUCT = "VENDOR_PRODUCT"
    PROTOCOL_TELEMETRY = "PROTOCOL_TELEMETRY"
    SCENARIO = "SCENARIO"
    INVESTIGATION = "INVESTIGATION"
    INDUSTRY = "INDUSTRY"


class PackMaturity(str, Enum):
    DRAFT = "DRAFT"
    BETA = "BETA"
    STABLE = "STABLE"
    PLANNED = "PLANNED"


class CustomSourceLifecycle(str, Enum):
    DRAFT = "DRAFT"
    SAMPLE_VERIFIED = "SAMPLE_VERIFIED"
    CONTRACT_VERIFIED = "CONTRACT_VERIFIED"
    SPLUNK_VERIFIED = "SPLUNK_VERIFIED"
    E2E_VALIDATED = "E2E_VALIDATED"
    READY = "READY"


class PromotionAuthority(str, Enum):
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class IntegrationRequirement(str, Enum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    NOT_REQUIRED = "NOT_REQUIRED"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"


class SplPortability(str, Enum):
    PRODUCTION_PORTABLE = "PRODUCTION_PORTABLE"
    NETSPOUT_SPECIFIC = "NETSPOUT_SPECIFIC"


class TelemetrySignal(str, Enum):
    LOGS = "LOGS"
    METRICS = "METRICS"
    TRACES = "TRACES"
    EVENTS = "EVENTS"
    FLOWS = "FLOWS"
    PACKETS = "PACKETS"


class ValidationStage(str, Enum):
    RAW_VERIFIED = "RAW_VERIFIED"
    SENT = "SENT"
    RECEIVER_OBSERVED = "RECEIVER_OBSERVED"
    SPLUNK_OBSERVED = "SPLUNK_OBSERVED"
    SOURCETYPE_VERIFIED = "SOURCETYPE_VERIFIED"
    FIELDS_VERIFIED = "FIELDS_VERIFIED"
    CIM_VERIFIED = "CIM_VERIFIED"


class ScenarioStage(str, Enum):
    BASELINE = "BASELINE"
    PRECURSOR = "PRECURSOR"
    INCIDENT = "INCIDENT"
    IMPACT = "IMPACT"
    DETECTION = "DETECTION"
    RECOVERY = "RECOVERY"


class ScenarioExperienceState(str, Enum):
    READY = "READY"
    PARTIAL = "PARTIAL"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


class VisualizationMode(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    CURATED = "CURATED"


class ValidationRequirement(str, Enum):
    REQUIRED = "REQUIRED"
    INFORMATIONAL = "INFORMATIONAL"


class RawFidelityPolicy(StrictModel):
    preserve_native_raw: bool
    modeled_values_may_change: bool = True
    structural_mutation_allowed: bool = False
    normalization_owner: str = "SPLUNK_INTEGRATION"
    cim_validation_stage: ValidationStage = ValidationStage.CIM_VERIFIED

    @model_validator(mode="after")
    def enforce_raw_fidelity(self):
        if not self.preserve_native_raw or self.structural_mutation_allowed:
            raise ValueError("source packs must preserve the native raw structure")
        if self.normalization_owner != "SPLUNK_INTEGRATION":
            raise ValueError("Splunk integrations, not generators, own normalization")
        if self.cim_validation_stage != ValidationStage.CIM_VERIFIED:
            raise ValueError("CIM validation must occur after Splunk ingestion")
        return self


class GeneratorDefinition(StrictModel):
    generator_id: str
    implementation_ref: Optional[str] = None
    source_ids: List[str]
    signals: List[TelemetrySignal]
    verification_state: VerificationState
    evidence_ids: List[str] = Field(default_factory=list)


class ValidatorDefinition(StrictModel):
    validator_id: str
    implementation_ref: Optional[str] = None
    source_ids: List[str]
    stages: List[ValidationStage]
    evidence_ids: List[str] = Field(default_factory=list)


class TransportCapability(StrictModel):
    transport_id: str
    component: str
    protocol: str
    signals: List[TelemetrySignal]
    compatible_source_ids: List[str] = Field(default_factory=list)
    verification_state: VerificationState
    implemented: bool = False
    evidence_ids: List[str] = Field(default_factory=list)
    notes: str = ""


class DestinationDefinition(StrictModel):
    destination_id: str
    destination_type: str
    accepted_transport_ids: List[str]
    verification_state: VerificationState
    evidence_ids: List[str] = Field(default_factory=list)


class SourcePackEntry(StrictModel):
    source: TelemetrySource
    generator_ids: List[str] = Field(default_factory=list)
    validator_ids: List[str] = Field(default_factory=list)
    compatible_transport_ids: List[str] = Field(default_factory=list)
    raw_fidelity: RawFidelityPolicy
    custom_lifecycle: Optional[CustomSourceLifecycle] = None
    sample_derived: bool = False
    ai_assisted_analysis: bool = False
    promotion_authority: Optional[PromotionAuthority] = None

    @model_validator(mode="after")
    def protect_imported_samples(self):
        if self.sample_derived:
            if self.custom_lifecycle is None:
                raise ValueError("sample-derived sources require an explicit lifecycle")
            if self.promotion_authority != PromotionAuthority.HUMAN_REVIEW_REQUIRED:
                raise ValueError("sample-derived source promotion requires human review")
            if "VENDOR_DOCUMENTED" in {
                item.value for item in self.source.provenance
            }:
                raise ValueError(
                    "a sample-derived source cannot claim vendor documentation"
                )
        return self


class CatalogSourceBinding(StrictModel):
    """Execution binding for a source owned by the authoritative base catalog."""

    source_id: str
    verification_state: VerificationState
    runtime_status: str
    generator_ids: List[str] = Field(default_factory=list)
    validator_ids: List[str] = Field(default_factory=list)
    compatible_transport_ids: List[str] = Field(default_factory=list)
    raw_fidelity: RawFidelityPolicy


class IntegrationRecommendation(StrictModel):
    recommendation_id: str
    source_id: str
    integration_id: Optional[str] = None
    requirement: IntegrationRequirement
    evidence_ids: List[str]
    notes: str = ""

    @model_validator(mode="after")
    def require_evidence(self):
        if not self.evidence_ids:
            raise ValueError("integration recommendations require evidence")
        if (
            self.requirement
            in {IntegrationRequirement.REQUIRED, IntegrationRequirement.RECOMMENDED}
            and not self.integration_id
        ):
            raise ValueError("required or recommended integrations need an integration")
        return self


class InvestigationRecipe(StrictModel):
    recipe_id: str
    title: str
    objective: Optional[str] = None
    question: Optional[str] = None
    expected_finding: Optional[str] = None
    explanation: Optional[str] = None
    hint: Optional[str] = None
    portability: SplPortability
    spl: str
    source_ids: List[str]
    required_fields: List[str] = Field(default_factory=list)
    cim_requirements: List[str] = Field(default_factory=list)
    netspout_only_fields: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_portability(self):
        if (
            self.portability == SplPortability.PRODUCTION_PORTABLE
            and self.netspout_only_fields
        ):
            raise ValueError("production-portable SPL cannot require NetSpout-only fields")
        if (
            self.portability == SplPortability.NETSPOUT_SPECIFIC
            and not self.netspout_only_fields
        ):
            raise ValueError("NetSpout-specific SPL must declare its lab-only fields")
        return self


class TopologyNode(StrictModel):
    node_id: str
    technology_id: str
    zone_id: str
    role: str
    source_ids: List[str] = Field(default_factory=list)
    label: Optional[str] = None
    entity_id: Optional[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None
    product: Optional[str] = None


class TopologyZone(StrictModel):
    zone_id: str
    label: str


class TopologyRelationship(StrictModel):
    relationship_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    protocol: Optional[str] = None
    purpose: Optional[str] = None
    telemetry_source_ids: List[str] = Field(default_factory=list)
    incident_relevance: Optional[str] = None


class TelemetryPath(StrictModel):
    path_id: str
    source_id: str
    producer_node_id: str
    observer_node_id: Optional[str] = None
    label: Optional[str] = None
    protocol: Optional[str] = None


class IncidentEvidence(StrictModel):
    incident_id: str
    source_ids: List[str]
    assertion: str
    corroboration_required: bool = True

    @model_validator(mode="after")
    def require_corroboration(self):
        if self.corroboration_required and len(set(self.source_ids)) < 2:
            raise ValueError("corroborated incidents require multiple evidence sources")
        return self


class TimelineStep(StrictModel):
    step_id: str
    stage: ScenarioStage
    description: str
    state_changes: Dict[str, str] = Field(default_factory=dict)
    entity_state_changes: Dict[str, str] = Field(default_factory=dict)
    telemetry_state_changes: Dict[str, str] = Field(default_factory=dict)
    expected_observations: List[str] = Field(default_factory=list)
    evidence_source_ids: List[str] = Field(default_factory=list)
    incident_ids: List[str] = Field(default_factory=list)


class GuidedInvestigationStep(StrictModel):
    step_id: str
    recipe_id: str
    title: str
    question: str
    expected_finding: str
    explanation: str
    hint: Optional[str] = None
    node_ids: List[str] = Field(default_factory=list)
    source_ids: List[str] = Field(default_factory=list)


class ScenarioValidationExpectation(StrictModel):
    validation_id: str
    label: str
    evidence_stage: str
    expected_state: str = "PROVEN"
    requirement: ValidationRequirement = ValidationRequirement.REQUIRED
    source_id: Optional[str] = None


class ScenarioVisualization(StrictModel):
    mode: VisualizationMode = VisualizationMode.AUTOMATIC
    direction: str = Field(default="LEFT_TO_RIGHT", pattern=r"^(LEFT_TO_RIGHT|TOP_TO_BOTTOM)$")
    curated_layout_ref: Optional[str] = None

    @model_validator(mode="after")
    def require_curated_layout(self):
        if self.mode == VisualizationMode.CURATED and not self.curated_layout_ref:
            raise ValueError("curated visualization requires a layout reference")
        return self


class ReplayPolicy(StrictModel):
    creates_new_run_id: bool = True
    preserves_history: bool = True
    reset_to_step: str = "RUN"

    @model_validator(mode="after")
    def preserve_run_boundaries(self):
        if not self.creates_new_run_id or not self.preserves_history:
            raise ValueError("scenario replay must create a new run and preserve history")
        return self


class ScenarioParameter(StrictModel):
    parameter_id: str
    value_type: str
    changes_modeled_values_only: bool = True

    @model_validator(mode="after")
    def protect_structure(self):
        if not self.changes_modeled_values_only:
            raise ValueError("scenario parameters cannot alter verified structure")
        return self


class GuidedScenarioManifest(StrictModel):
    scenario_id: str
    title: str
    description: str
    story: str
    domain: Optional[str] = None
    category: Optional[str] = None
    technical_description: Optional[str] = None
    difficulty: str
    expected_duration_minutes: int = Field(ge=1)
    learning_objectives: List[str]
    skills_practiced: List[str] = Field(default_factory=list)
    expected_outcome: Optional[str] = None
    baseline_description: Optional[str] = None
    incident_description: Optional[str] = None
    discovery_prompt: Optional[str] = None
    learning_hints: List[str] = Field(default_factory=list)
    business_impact: str
    prerequisites: List[str] = Field(default_factory=list)
    technology_ids: List[str]
    source_ids: List[str]
    entities: List[str]
    zones: List[TopologyZone]
    nodes: List[TopologyNode]
    relationships: List[TopologyRelationship]
    telemetry_paths: List[TelemetryPath]
    incident_path: List[str]
    incident_summary: Optional[str] = None
    runtime_state_keys: List[str]
    timeline: List[TimelineStep]
    incidents: List[IncidentEvidence]
    parameters: List[ScenarioParameter] = Field(default_factory=list)
    integration_recommendation_ids: List[str] = Field(default_factory=list)
    expected_evidence: List[str]
    investigation_recipe_ids: List[str] = Field(default_factory=list)
    investigation_steps: List[GuidedInvestigationStep] = Field(default_factory=list)
    validation_expectations: List[ScenarioValidationExpectation] = Field(
        default_factory=list
    )
    visualization: ScenarioVisualization = Field(default_factory=ScenarioVisualization)
    replay_policy: Optional[ReplayPolicy] = None
    troubleshooting_steps: List[str] = Field(default_factory=list)
    cim_validation: List[str] = Field(default_factory=list)
    production_replication_guidance: List[str] = Field(default_factory=list)
    curated_layout_ref: Optional[str] = None

    @model_validator(mode="after")
    def validate_graph_and_timeline(self):
        source_ids = set(self.source_ids)
        zone_ids = _unique_values(self.zones, "zone_id", self.scenario_id)
        node_ids = _unique_values(self.nodes, "node_id", self.scenario_id)
        incident_ids = _unique_values(self.incidents, "incident_id", self.scenario_id)
        _unique_values(self.relationships, "relationship_id", self.scenario_id)
        _unique_values(self.telemetry_paths, "path_id", self.scenario_id)
        _unique_values(self.timeline, "step_id", self.scenario_id)
        _unique_values(self.investigation_steps, "step_id", self.scenario_id)
        _unique_values(
            self.validation_expectations, "validation_id", self.scenario_id
        )
        _require_refs(self.incident_path, node_ids, self.scenario_id, "node")
        for node in self.nodes:
            _require_refs([node.zone_id], zone_ids, node.node_id, "zone")
            _require_refs(node.source_ids, source_ids, node.node_id, "source")
        for relationship in self.relationships:
            _require_refs(
                [relationship.source_node_id, relationship.target_node_id],
                node_ids,
                relationship.relationship_id,
                "node",
            )
            _require_refs(
                relationship.telemetry_source_ids,
                source_ids,
                relationship.relationship_id,
                "source",
            )
        for path in self.telemetry_paths:
            _require_refs([path.source_id], source_ids, path.path_id, "source")
            node_refs = [path.producer_node_id]
            if path.observer_node_id:
                node_refs.append(path.observer_node_id)
            _require_refs(node_refs, node_ids, path.path_id, "node")
        for incident in self.incidents:
            _require_refs(incident.source_ids, source_ids, incident.incident_id, "source")
        for step in self.timeline:
            _require_refs(step.incident_ids, incident_ids, step.step_id, "incident")
            _require_refs(
                step.entity_state_changes.keys(), node_ids, step.step_id, "node"
            )
            _require_refs(
                step.telemetry_state_changes.keys(),
                source_ids,
                step.step_id,
                "source",
            )
            _require_refs(
                step.evidence_source_ids, source_ids, step.step_id, "source"
            )
        for step in self.investigation_steps:
            _require_refs(step.node_ids, node_ids, step.step_id, "node")
            _require_refs(step.source_ids, source_ids, step.step_id, "source")
        for expectation in self.validation_expectations:
            if expectation.source_id:
                _require_refs(
                    [expectation.source_id],
                    source_ids,
                    expectation.validation_id,
                    "source",
                )
        stage_order = [list(ScenarioStage).index(item.stage) for item in self.timeline]
        if stage_order != sorted(stage_order):
            raise ValueError("scenario timeline stages must be chronological")
        return self


def evaluate_guided_scenario_completeness(
    scenario: GuidedScenarioManifest,
    *,
    executable: bool,
    provenance_available: bool,
    verification_state: VerificationState,
) -> Dict[str, object]:
    """Evaluate guided-lab readiness without promoting scenario verification."""

    checks = {
        "story": bool(
            scenario.story
            and scenario.technical_description
            and scenario.baseline_description
            and scenario.incident_description
        ),
        "environment": bool(
            scenario.entities
            and scenario.technology_ids
            and scenario.zones
            and scenario.nodes
        ),
        "topology": bool(scenario.nodes and scenario.zones and scenario.relationships),
        "telemetry_manifest": bool(
            scenario.source_ids
            and scenario.telemetry_paths
            and scenario.expected_evidence
        ),
        "prerequisites": bool(scenario.prerequisites),
        "execution": executable,
        "evidence": bool(scenario.expected_evidence),
        "investigation": bool(
            scenario.investigation_recipe_ids and scenario.investigation_steps
        ),
        "expected_findings": bool(
            scenario.investigation_steps
            and all(step.expected_finding for step in scenario.investigation_steps)
        ),
        "validation": bool(scenario.validation_expectations),
        "replay_reset": scenario.replay_policy is not None,
        "provenance": provenance_available,
    }
    if verification_state == VerificationState.UNSUPPORTED:
        state = ScenarioExperienceState.UNSUPPORTED
    elif verification_state == VerificationState.RESEARCH_REQUIRED:
        state = ScenarioExperienceState.RESEARCH_REQUIRED
    elif all(checks.values()) and verification_state == VerificationState.VERIFIED:
        state = ScenarioExperienceState.READY
    else:
        state = ScenarioExperienceState.PARTIAL
    return {
        "state": state.value,
        "passed": sum(1 for value in checks.values() if value),
        "total": len(checks),
        "checks": checks,
        "production_guidance_available": bool(
            scenario.production_replication_guidance
        ),
    }


class IndustryAssociation(StrictModel):
    industry_id: str
    name: str
    source_ids: List[str]
    scenario_ids: List[str] = Field(default_factory=list)


class PackDefinition(StrictModel):
    pack_id: str
    pack_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    kind: PackKind
    display_name: str
    maturity: PackMaturity
    verification_state: VerificationState
    dependencies: List[str] = Field(default_factory=list)
    evidence: List[EvidenceReference] = Field(default_factory=list)
    sources: List[SourcePackEntry] = Field(default_factory=list)
    integrations: List[SplunkIntegration] = Field(default_factory=list)
    generators: List[GeneratorDefinition] = Field(default_factory=list)
    validators: List[ValidatorDefinition] = Field(default_factory=list)
    transports: List[TransportCapability] = Field(default_factory=list)
    destinations: List[DestinationDefinition] = Field(default_factory=list)
    integration_recommendations: List[IntegrationRecommendation] = Field(
        default_factory=list
    )
    scenarios: List[GuidedScenarioManifest] = Field(default_factory=list)
    investigations: List[InvestigationRecipe] = Field(default_factory=list)
    industries: List[IndustryAssociation] = Field(default_factory=list)


class SourceBinding(StrictModel):
    source_id: str
    generator_id: str
    transport_id: str
    destination_id: str
    validator_ids: List[str] = Field(default_factory=list)


class CompositionDefinition(StrictModel):
    composition_id: str
    scenario_id: str
    pack_ids: List[str]
    source_bindings: List[SourceBinding]
    investigation_recipe_ids: List[str] = Field(default_factory=list)


class PackRegistry(StrictModel):
    schema_version: str
    registry_version: str
    catalog_evidence_ids: List[str] = Field(default_factory=list)
    catalog_integration_ids: List[str] = Field(default_factory=list)
    catalog_source_bindings: List[CatalogSourceBinding] = Field(default_factory=list)
    packs: List[PackDefinition]
    compositions: List[CompositionDefinition]

    @model_validator(mode="after")
    def validate_registry(self):
        pack_ids = _unique_values(self.packs, "pack_id", "pack registry")
        resources = self._resources()
        for pack in self.packs:
            _require_refs(pack.dependencies, pack_ids, pack.pack_id, "pack")
        _reject_dependency_cycles(
            {pack.pack_id: set(pack.dependencies) for pack in self.packs}
        )

        # Reuse the authoritative Phase 2 trust validator for all pack-owned
        # evidence, source contracts, sourcetypes, and integrations.
        TelemetryCatalog(
            schema_version=self.schema_version,
            catalog_version=self.registry_version,
            evidence=resources["evidence"],
            integrations=resources["integrations"],
            sources=[entry.source for entry in resources["source_entries"]],
            source_manifests=[],
        )

        evidence_ids = _unique_values(resources["evidence"], "evidence_id", "packs")
        evidence_ids.update(self.catalog_evidence_ids)
        source_ids = _unique_values(
            [entry.source for entry in resources["source_entries"]],
            "source_id",
            "packs",
        )
        catalog_source_ids = _unique_values(
            self.catalog_source_bindings, "source_id", "catalog source bindings"
        )
        if source_ids.intersection(catalog_source_ids):
            raise ValueError("pack sources cannot duplicate base catalog sources")
        source_ids.update(catalog_source_ids)
        generator_ids = _unique_values(resources["generators"], "generator_id", "packs")
        validator_ids = _unique_values(resources["validators"], "validator_id", "packs")
        transport_ids = _unique_values(resources["transports"], "transport_id", "packs")
        destination_ids = _unique_values(
            resources["destinations"], "destination_id", "packs"
        )
        integration_ids = _unique_values(
            resources["integrations"], "integration_id", "packs"
        )
        integration_ids.update(self.catalog_integration_ids)
        recommendation_ids = _unique_values(
            resources["recommendations"], "recommendation_id", "packs"
        )
        scenario_ids = _unique_values(resources["scenarios"], "scenario_id", "packs")
        recipe_ids = _unique_values(resources["investigations"], "recipe_id", "packs")
        _unique_values(resources["industries"], "industry_id", "packs")

        for item in resources["generators"]:
            _require_refs(item.source_ids, source_ids, item.generator_id, "source")
            _require_refs(item.evidence_ids, evidence_ids, item.generator_id, "evidence")
        for item in resources["validators"]:
            _require_refs(item.source_ids, source_ids, item.validator_id, "source")
            _require_refs(item.evidence_ids, evidence_ids, item.validator_id, "evidence")
        for item in resources["transports"]:
            _require_refs(
                item.compatible_source_ids, source_ids, item.transport_id, "source"
            )
            _require_refs(item.evidence_ids, evidence_ids, item.transport_id, "evidence")
        for item in resources["destinations"]:
            _require_refs(
                item.accepted_transport_ids,
                transport_ids,
                item.destination_id,
                "transport",
            )
            _require_refs(
                item.evidence_ids, evidence_ids, item.destination_id, "evidence"
            )
        for entry in resources["source_entries"]:
            owner = entry.source.source_id
            _require_refs(entry.generator_ids, generator_ids, owner, "generator")
            _require_refs(entry.validator_ids, validator_ids, owner, "validator")
            _require_refs(
                entry.compatible_transport_ids, transport_ids, owner, "transport"
            )
        for entry in self.catalog_source_bindings:
            owner = entry.source_id
            _require_refs(entry.generator_ids, generator_ids, owner, "generator")
            _require_refs(entry.validator_ids, validator_ids, owner, "validator")
            _require_refs(
                entry.compatible_transport_ids, transport_ids, owner, "transport"
            )
        for item in resources["recommendations"]:
            _require_refs([item.source_id], source_ids, item.recommendation_id, "source")
            if item.integration_id:
                _require_refs(
                    [item.integration_id],
                    integration_ids,
                    item.recommendation_id,
                    "integration",
                )
                local_integrations = {
                    value.integration_id: value for value in resources["integrations"]
                }
                if item.integration_id in local_integrations:
                    integration = local_integrations[item.integration_id]
                    if item.source_id not in integration.supported_source_ids:
                        raise ValueError(
                            "integration recommendation relationship is not explicit"
                        )
            _require_refs(
                item.evidence_ids, evidence_ids, item.recommendation_id, "evidence"
            )
        for item in resources["scenarios"]:
            _require_refs(item.source_ids, source_ids, item.scenario_id, "source")
            _require_refs(
                item.integration_recommendation_ids,
                recommendation_ids,
                item.scenario_id,
                "integration recommendation",
            )
            _require_refs(
                item.investigation_recipe_ids,
                recipe_ids,
                item.scenario_id,
                "investigation recipe",
            )
            _require_refs(
                [step.recipe_id for step in item.investigation_steps],
                recipe_ids,
                item.scenario_id,
                "investigation recipe",
            )
        for item in resources["investigations"]:
            _require_refs(item.source_ids, source_ids, item.recipe_id, "source")
            _require_refs(item.evidence_ids, evidence_ids, item.recipe_id, "evidence")
        for item in resources["industries"]:
            _require_refs(item.source_ids, source_ids, item.industry_id, "source")
            _require_refs(item.scenario_ids, scenario_ids, item.industry_id, "scenario")

        _unique_values(self.compositions, "composition_id", "pack registry")
        source_entries = {
            item.source.source_id: item for item in resources["source_entries"]
        }
        source_entries.update(
            {item.source_id: item for item in self.catalog_source_bindings}
        )
        generators = {item.generator_id: item for item in resources["generators"]}
        transports = {item.transport_id: item for item in resources["transports"]}
        destinations = {
            item.destination_id: item for item in resources["destinations"]
        }
        scenarios = {item.scenario_id: item for item in resources["scenarios"]}
        for composition in self.compositions:
            _require_refs(composition.pack_ids, pack_ids, composition.composition_id, "pack")
            _require_refs(
                [composition.scenario_id],
                scenario_ids,
                composition.composition_id,
                "scenario",
            )
            _require_refs(
                composition.investigation_recipe_ids,
                recipe_ids,
                composition.composition_id,
                "investigation recipe",
            )
            scenario = scenarios[composition.scenario_id]
            bound_sources = {item.source_id for item in composition.source_bindings}
            if bound_sources != set(scenario.source_ids):
                raise ValueError("composition must bind every scenario source exactly once")
            for binding in composition.source_bindings:
                _require_refs([binding.generator_id], generator_ids, binding.source_id, "generator")
                _require_refs([binding.transport_id], transport_ids, binding.source_id, "transport")
                _require_refs(
                    [binding.destination_id],
                    destination_ids,
                    binding.source_id,
                    "destination",
                )
                _require_refs(binding.validator_ids, validator_ids, binding.source_id, "validator")
                source = source_entries[binding.source_id]
                source_state = (
                    source.source.verification_state
                    if isinstance(source, SourcePackEntry)
                    else source.verification_state
                )
                if source_state in {
                    VerificationState.RESEARCH_REQUIRED,
                    VerificationState.UNSUPPORTED,
                }:
                    raise ValueError("non-runnable source cannot be composed")
                if binding.generator_id not in source.generator_ids:
                    raise ValueError("source binding uses an incompatible generator")
                if binding.source_id not in generators[binding.generator_id].source_ids:
                    raise ValueError("generator does not declare the bound source")
                if binding.transport_id not in source.compatible_transport_ids:
                    raise ValueError("source binding uses an incompatible transport")
                if (
                    not transports[binding.transport_id].implemented
                    or transports[binding.transport_id].verification_state
                    in {
                        VerificationState.RESEARCH_REQUIRED,
                        VerificationState.UNSUPPORTED,
                    }
                ):
                    raise ValueError("non-runnable transport cannot be composed")
                if (
                    transports[binding.transport_id].compatible_source_ids
                    and binding.source_id
                    not in transports[binding.transport_id].compatible_source_ids
                ):
                    raise ValueError("transport does not declare the bound source")
                if binding.transport_id not in destinations[
                    binding.destination_id
                ].accepted_transport_ids:
                    raise ValueError("destination does not accept the bound transport")
        return self

    def _resources(self):
        return {
            "evidence": [item for pack in self.packs for item in pack.evidence],
            "source_entries": [item for pack in self.packs for item in pack.sources],
            "integrations": [item for pack in self.packs for item in pack.integrations],
            "generators": [item for pack in self.packs for item in pack.generators],
            "validators": [item for pack in self.packs for item in pack.validators],
            "transports": [item for pack in self.packs for item in pack.transports],
            "destinations": [item for pack in self.packs for item in pack.destinations],
            "recommendations": [
                item for pack in self.packs for item in pack.integration_recommendations
            ],
            "scenarios": [item for pack in self.packs for item in pack.scenarios],
            "investigations": [item for pack in self.packs for item in pack.investigations],
            "industries": [item for pack in self.packs for item in pack.industries],
        }

    def validate_against_catalog(self, catalog: TelemetryCatalog) -> None:
        """Validate all declared base-catalog references against authoritative data."""
        evidence_ids = {item.evidence_id for item in catalog.evidence}
        integration_by_id = {
            item.integration_id: item for item in catalog.integrations
        }
        source_by_id = {item.source_id: item for item in catalog.sources}
        _require_refs(
            self.catalog_evidence_ids,
            evidence_ids,
            self.registry_version,
            "catalog evidence",
        )
        _require_refs(
            self.catalog_integration_ids,
            set(integration_by_id),
            self.registry_version,
            "catalog integration",
        )
        _require_refs(
            [item.source_id for item in self.catalog_source_bindings],
            set(source_by_id),
            self.registry_version,
            "catalog source",
        )
        for binding in self.catalog_source_bindings:
            source = source_by_id[binding.source_id]
            if source.verification_state != binding.verification_state:
                raise ValueError(
                    "catalog source binding '{}' verification state is stale".format(
                        binding.source_id
                    )
                )
            if source.netspout_contract.runtime_status != binding.runtime_status:
                raise ValueError(
                    "catalog source binding '{}' runtime status is stale".format(
                        binding.source_id
                    )
                )
        for recommendation in self._resources()["recommendations"]:
            if recommendation.integration_id in integration_by_id:
                integration = integration_by_id[recommendation.integration_id]
                if recommendation.source_id not in integration.supported_source_ids:
                    raise ValueError(
                        "catalog integration recommendation relationship is not explicit"
                    )


def _unique_values(items, field: str, owner: str) -> Set[str]:
    result: Set[str] = set()
    for item in items:
        value = getattr(item, field)
        if value in result:
            raise ValueError("duplicate {} in {}".format(field, owner))
        result.add(value)
    return result


def _require_refs(
    references: List[str], valid_ids: Set[str], owner: str, label: str
) -> None:
    missing = sorted(set(references) - valid_ids)
    if missing:
        raise ValueError(
            "{} '{}' references unknown values: {}".format(
                label, owner, ", ".join(missing)
            )
        )


def _reject_dependency_cycles(graph: Dict[str, Set[str]]) -> None:
    visiting: Set[str] = set()
    visited: Set[str] = set()

    def visit(pack_id: str) -> None:
        if pack_id in visiting:
            raise ValueError("pack dependency cycle includes '{}'".format(pack_id))
        if pack_id in visited:
            return
        visiting.add(pack_id)
        for dependency in graph[pack_id]:
            visit(dependency)
        visiting.remove(pack_id)
        visited.add(pack_id)

    for pack_id in graph:
        visit(pack_id)
