"""Versioned, industry-neutral business dependency packs for Phase 10.

Industry packs contain context and modeled dependency impact only. They
reference executable Scenario Packs and Source Contracts owned by the core
catalog; they never define native telemetry structures.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import Field, model_validator

from netspout_core.catalog_contracts import EvidenceReference, StrictModel


class EvidenceClassification(str, Enum):
    OBSERVED = "OBSERVED"
    MODELED = "MODELED"
    INFERRED = "INFERRED"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


class IndustryEntityKind(str, Enum):
    BUSINESS_CAPABILITY = "BUSINESS_CAPABILITY"
    BUSINESS_SERVICE = "BUSINESS_SERVICE"
    APPLICATION = "APPLICATION"
    INFRASTRUCTURE_SERVICE = "INFRASTRUCTURE_SERVICE"
    NETWORK = "NETWORK"
    DEVICE = "DEVICE"
    SECURITY_ZONE = "SECURITY_ZONE"
    SITE = "SITE"
    OPERATIONAL_PROCESS = "OPERATIONAL_PROCESS"


class IndustryEntity(StrictModel):
    entity_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    label: str
    entity_kind: IndustryEntityKind
    zone_id: str
    description: str
    attributes: Dict[str, str] = Field(default_factory=dict)


class IndustryDependency(StrictModel):
    dependency_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    criticality: str
    assumption: str


class BusinessCapability(StrictModel):
    capability_id: str
    name: str
    description: str
    objective: str
    entity_id: str


class OperationalObjective(StrictModel):
    objective_id: str
    name: str
    statement: str
    measurement_status: EvidenceClassification

    @model_validator(mode="after")
    def reject_fake_measurement(self):
        if self.measurement_status == EvidenceClassification.OBSERVED:
            raise ValueError(
                "industry objectives cannot be OBSERVED without a telemetry contract"
            )
        return self


class BusinessImpactModel(StrictModel):
    impact_id: str
    title: str
    statement: str
    classification: EvidenceClassification
    trigger_entity_ids: List[str]
    impacted_entity_ids: List[str]
    dependency_ids: List[str]
    assumptions: List[str]
    exclusions: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_transparent_model(self):
        if self.classification == EvidenceClassification.OBSERVED:
            raise ValueError(
                "business impact cannot be marked OBSERVED by an Industry Pack"
            )
        if not self.assumptions:
            raise ValueError("modeled business impact requires declared assumptions")
        return self


class TelemetryRequirement(StrictModel):
    source_id: str
    role: str
    required: bool = True
    evidence_classification: EvidenceClassification = (
        EvidenceClassification.OBSERVED
    )
    notes: str = ""


class IndustryEnvironment(StrictModel):
    environment_id: str
    name: str
    description: str
    infrastructure_archetype: str
    entity_ids: List[str]
    dependency_ids: List[str]
    scenario_ids: List[str]
    default_scenario_id: str
    telemetry_source_ids: List[str]
    investigation_objectives: List[str]


class IndustryPack(StrictModel):
    pack_id: str
    industry_id: str
    pack_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    name: str
    description: str
    implemented_scope: str
    maturity: str
    business_capabilities: List[BusinessCapability]
    environments: List[IndustryEnvironment]
    entities: List[IndustryEntity]
    dependencies: List[IndustryDependency]
    operational_objectives: List[OperationalObjective]
    business_impacts: List[BusinessImpactModel]
    telemetry_requirements: List[TelemetryRequirement]
    provenance_evidence_ids: List[str]
    validation_requirements: List[str]
    dashboard_metadata_version: str = "1.0.0"

    @model_validator(mode="after")
    def validate_shared_graph(self):
        entity_ids = _unique(self.entities, "entity_id", self.industry_id)
        dependency_ids = _unique(
            self.dependencies, "dependency_id", self.industry_id
        )
        capability_ids = _unique(
            self.business_capabilities, "capability_id", self.industry_id
        )
        _unique(self.environments, "environment_id", self.industry_id)
        _unique(self.business_impacts, "impact_id", self.industry_id)
        _unique(
            self.operational_objectives, "objective_id", self.industry_id
        )
        if not capability_ids:
            raise ValueError("industry packs require a business capability")
        for capability in self.business_capabilities:
            _require(
                [capability.entity_id],
                entity_ids,
                capability.capability_id,
                "entity",
            )
        for dependency in self.dependencies:
            _require(
                [dependency.source_entity_id, dependency.target_entity_id],
                entity_ids,
                dependency.dependency_id,
                "entity",
            )
        _reject_dependency_cycles(self.dependencies)
        for environment in self.environments:
            _require(
                environment.entity_ids,
                entity_ids,
                environment.environment_id,
                "entity",
            )
            _require(
                environment.dependency_ids,
                dependency_ids,
                environment.environment_id,
                "dependency",
            )
            if environment.default_scenario_id not in environment.scenario_ids:
                raise ValueError(
                    "{} default scenario must be available".format(
                        environment.environment_id
                    )
                )
        for impact in self.business_impacts:
            _require(
                impact.trigger_entity_ids + impact.impacted_entity_ids,
                entity_ids,
                impact.impact_id,
                "entity",
            )
            _require(
                impact.dependency_ids,
                dependency_ids,
                impact.impact_id,
                "dependency",
            )
        return self


class IndustryRegistry(StrictModel):
    schema_version: str
    registry_version: str
    evidence: List[EvidenceReference]
    industries: List[IndustryPack]

    @model_validator(mode="after")
    def validate_registry(self):
        evidence_ids = _unique(self.evidence, "evidence_id", "industry registry")
        _unique(self.industries, "industry_id", "industry registry")
        _unique(self.industries, "pack_id", "industry registry")
        for industry in self.industries:
            _require(
                industry.provenance_evidence_ids,
                evidence_ids,
                industry.industry_id,
                "evidence",
            )
        return self


class IndustrySelection(StrictModel):
    industry_id: str
    environment_id: str
    scenario_id: Optional[str] = None
    seed: int = Field(default=1010, ge=0, le=2_147_483_647)
    modeled_parameters: Dict[str, Any] = Field(default_factory=dict)


def _unique(items: List[Any], field: str, owner: str) -> Set[str]:
    values = [str(getattr(item, field)) for item in items]
    if len(values) != len(set(values)):
        raise ValueError("{} contains duplicate {}".format(owner, field))
    return set(values)


def _require(values: List[str], available: Set[str], owner: str, kind: str) -> None:
    missing = sorted(set(values) - available)
    if missing:
        raise ValueError(
            "{} references unknown {}: {}".format(owner, kind, ", ".join(missing))
        )


def _reject_dependency_cycles(dependencies: List[IndustryDependency]) -> None:
    graph: Dict[str, Set[str]] = {}
    for item in dependencies:
        graph.setdefault(item.source_entity_id, set()).add(item.target_entity_id)

    visiting: Set[str] = set()
    visited: Set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError("industry dependency graph contains a cycle")
        if node in visited:
            return
        visiting.add(node)
        for target in graph.get(node, set()):
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


class IndustryPackService:
    """Discovers packs and evaluates causal impact without generating logs."""

    def __init__(self, registry: IndustryRegistry, pack_registry: Any):
        self.registry = registry
        self.pack_registry = pack_registry
        self._industries = {
            item.industry_id: item for item in registry.industries
        }
        self._scenarios = {
            item.scenario_id: item
            for pack in pack_registry.packs
            for item in pack.scenarios
        }
        self._recipes = {
            item.recipe_id: item
            for pack in pack_registry.packs
            for item in pack.investigations
        }
        self._validate_runtime_references()

    def _validate_runtime_references(self) -> None:
        source_ids = {
            item.source.source_id
            for pack in self.pack_registry.packs
            for item in pack.sources
        }
        source_ids.update(
            item.source_id for item in self.pack_registry.catalog_source_bindings
        )
        for industry in self.registry.industries:
            required_sources = {
                item.source_id for item in industry.telemetry_requirements
            }
            _require(
                list(required_sources),
                source_ids,
                industry.industry_id,
                "source",
            )
            for environment in industry.environments:
                _require(
                    environment.scenario_ids,
                    set(self._scenarios),
                    environment.environment_id,
                    "scenario",
                )
                scenario_sources = set(
                    self._scenarios[environment.default_scenario_id].source_ids
                )
                _require(
                    environment.telemetry_source_ids,
                    scenario_sources,
                    environment.environment_id,
                    "default scenario source",
                )

    def catalog(self) -> Dict[str, Any]:
        return {
            "schema_version": self.registry.schema_version,
            "registry_version": self.registry.registry_version,
            "evidence": [
                item.model_dump(mode="json") for item in self.registry.evidence
            ],
            "industries": [self.describe(item) for item in self.registry.industries],
            "future_categories": [
                "Retail",
                "Telecommunications",
                "Energy",
                "Utilities",
                "Transportation",
                "Logistics",
                "Government",
                "Education",
                "Hospitality",
                "Media",
                "Technology",
                "Agriculture",
                "Critical Infrastructure",
            ],
        }

    def get(self, industry_id: str) -> Optional[IndustryPack]:
        return self._industries.get(industry_id)

    def describe(self, industry: IndustryPack) -> Dict[str, Any]:
        data = industry.model_dump(mode="json")
        scenario_ids = {
            scenario_id
            for environment in industry.environments
            for scenario_id in environment.scenario_ids
        }
        data["scenario_references"] = [
            {
                "scenario_id": scenario_id,
                "title": self._scenarios[scenario_id].title,
                "source_ids": self._scenarios[scenario_id].source_ids,
                "investigation_recipe_ids": self._scenarios[
                    scenario_id
                ].investigation_recipe_ids,
                "scenario_maturity": self._scenarios[
                    scenario_id
                ].scenario_maturity,
            }
            for scenario_id in sorted(scenario_ids)
        ]
        return data

    def compose(self, selection: IndustrySelection) -> Dict[str, Any]:
        industry = self.get(selection.industry_id)
        if industry is None:
            raise ValueError("unknown industry")
        environment = next(
            (
                item
                for item in industry.environments
                if item.environment_id == selection.environment_id
            ),
            None,
        )
        if environment is None:
            raise ValueError("unknown industry environment")
        scenario_id = selection.scenario_id or environment.default_scenario_id
        if scenario_id not in environment.scenario_ids:
            raise ValueError(
                "scenario is not compatible with the selected environment"
            )
        supported_modeled_parameters = {
            "affected_entity_ids",
            "impact_assumptions",
        }
        unsupported_parameters = sorted(
            set(selection.modeled_parameters) - supported_modeled_parameters
        )
        if unsupported_parameters:
            raise ValueError(
                "unsupported modeled parameter(s): {}; Industry Packs cannot "
                "request undeclared telemetry, protocol, or vendor fields".format(
                    ", ".join(unsupported_parameters)
                )
            )
        affected_entity_ids = selection.modeled_parameters.get(
            "affected_entity_ids", environment.entity_ids[:1]
        )
        if not isinstance(affected_entity_ids, list) or not all(
            isinstance(item, str) for item in affected_entity_ids
        ):
            raise ValueError("affected_entity_ids must be a list of entity IDs")
        impact_assumptions = selection.modeled_parameters.get(
            "impact_assumptions", []
        )
        if not isinstance(impact_assumptions, list) or not all(
            isinstance(item, str) and item.strip() for item in impact_assumptions
        ):
            raise ValueError("impact_assumptions must be a list of non-empty strings")
        scenario = self._scenarios[scenario_id]
        return {
            "industry_id": industry.industry_id,
            "environment_id": environment.environment_id,
            "scenario_id": scenario_id,
            "seed": selection.seed,
            "modeled_parameters": selection.modeled_parameters,
            "source_ids": scenario.source_ids,
            "investigation_recipe_ids": scenario.investigation_recipe_ids,
            "entity_ids": environment.entity_ids,
            "dependency_ids": environment.dependency_ids,
            "technical_evidence_classification": EvidenceClassification.NOT_ESTABLISHED.value,
            "business_impact_classification": EvidenceClassification.MODELED.value,
            "generation_request": {
                "mode": "SCENARIO",
                "selection_id": scenario_id,
                "transport_id": "transport-local-hec",
                "destination_id": "destination-local-docker-splunk",
                "count": 1,
                "rate_eps": 1.0,
                "scenario_parameters": {
                    "seed": selection.seed,
                },
            },
            "impact_preview": self.propagate(
                industry.industry_id,
                environment.environment_id,
                affected_entity_ids,
            ),
        }

    def propagate(
        self,
        industry_id: str,
        environment_id: str,
        affected_entity_ids: List[str],
    ) -> Dict[str, Any]:
        industry = self.get(industry_id)
        if industry is None:
            raise ValueError("unknown industry")
        environment = next(
            (
                item
                for item in industry.environments
                if item.environment_id == environment_id
            ),
            None,
        )
        if environment is None:
            raise ValueError("unknown industry environment")
        allowed_entities = set(environment.entity_ids)
        _require(
            affected_entity_ids,
            allowed_entities,
            environment_id,
            "affected entity",
        )
        dependencies = [
            item
            for item in industry.dependencies
            if item.dependency_id in environment.dependency_ids
        ]
        impacted = set(affected_entity_ids)
        changed = True
        while changed:
            changed = False
            for dependency in dependencies:
                if (
                    dependency.source_entity_id in impacted
                    and dependency.target_entity_id not in impacted
                ):
                    impacted.add(dependency.target_entity_id)
                    changed = True
        impact_results = []
        for model in industry.business_impacts:
            if (
                set(model.trigger_entity_ids).intersection(impacted)
                and set(model.impacted_entity_ids).intersection(impacted)
            ):
                impact_results.append(
                    {
                        **model.model_dump(mode="json"),
                        "status": model.classification.value,
                    }
                )
        return {
            "industry_id": industry_id,
            "environment_id": environment_id,
            "affected_entity_ids": affected_entity_ids,
            "propagated_entity_ids": sorted(impacted),
            "dependency_ids": [
                item.dependency_id
                for item in dependencies
                if item.source_entity_id in impacted
                and item.target_entity_id in impacted
            ],
            "technical_evidence": {
                "status": EvidenceClassification.NOT_ESTABLISHED.value,
                "detail": (
                    "Technical evidence becomes OBSERVED only after the referenced "
                    "scenario proves receiver and Splunk observation."
                ),
            },
            "business_impacts": impact_results,
        }


def extend_registry(base_registry: Dict[str, Any], specification: Dict[str, Any]):
    """Register discoverable INDUSTRY Packs without copying scenarios/sources."""

    merged = {
        **base_registry,
        "packs": list(base_registry.get("packs", [])),
        "compositions": list(base_registry.get("compositions", [])),
    }
    for industry in specification.get("industries", []):
        source_ids = sorted(
            {
                item["source_id"]
                for item in industry.get("telemetry_requirements", [])
            }
        )
        scenario_ids = sorted(
            {
                scenario_id
                for environment in industry.get("environments", [])
                for scenario_id in environment.get("scenario_ids", [])
            }
        )
        merged["packs"].append(
            {
                "pack_id": industry["pack_id"],
                "pack_version": industry["pack_version"],
                "kind": "INDUSTRY",
                "display_name": industry["name"],
                "maturity": "STABLE",
                "verification_state": "VERIFIED",
                "dependencies": [],
                "evidence": [],
                "sources": [],
                "integrations": [],
                "generators": [],
                "validators": [],
                "transports": [],
                "destinations": [],
                "declarative_templates": [],
                "integration_recommendations": [],
                "scenarios": [],
                "investigations": [],
                "industries": [
                    {
                        "industry_id": industry["industry_id"],
                        "name": industry["name"],
                        "source_ids": source_ids,
                        "scenario_ids": scenario_ids,
                    }
                ],
            }
        )
    return merged
