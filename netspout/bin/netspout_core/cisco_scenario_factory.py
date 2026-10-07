"""Vendor-neutral scenario-definition factory and maturity enforcement.

The factory catalogs scenario intent separately from executable runtime Packs.
Only records whose evidence satisfies a maturity gate may claim that maturity.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from enum import Enum
import json
import os
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Set

from pydantic import Field, model_validator

from netspout_core.catalog_contracts import StrictModel


class ScenarioMaturity(str, Enum):
    CANDIDATE = "CANDIDATE"
    RESEARCHED = "RESEARCHED"
    CONTRACTED = "CONTRACTED"
    FORMAT_VALIDATED = "FORMAT_VALIDATED"
    RUNTIME_VALIDATED = "RUNTIME_VALIDATED"
    SPLUNK_VALIDATED = "SPLUNK_VALIDATED"
    GOLDEN = "GOLDEN"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    BLOCKED = "BLOCKED"


class CimState(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    DOCUMENTED = "DOCUMENTED"
    EXPECTED = "EXPECTED"
    RUNTIME_VALIDATED = "RUNTIME_VALIDATED"


class ValidationState(str, Enum):
    DEFINITION_VALIDATED = "DEFINITION_VALIDATED"
    RESEARCH_BLOCKED = "RESEARCH_BLOCKED"
    UNSUPPORTED = "UNSUPPORTED"
    BLOCKED = "BLOCKED"
    LIVE_VALIDATED = "LIVE_VALIDATED"


class TimelineTransition(StrictModel):
    stage: str
    state_changes: Dict[str, str] = Field(default_factory=dict)
    offset_seconds: int = Field(ge=0)
    expected_observation: str


class InvestigationPackRef(StrictModel):
    status: str
    recipe_ids: List[str] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    expected_findings: List[str] = Field(default_factory=list)
    spl_classifications: List[str] = Field(default_factory=list)


class TroubleshootingPackRef(StrictModel):
    status: str
    operation_ids: List[str] = Field(default_factory=list)
    research_required: List[str] = Field(default_factory=list)


class ProductionPortability(StrictModel):
    status: str
    guide_id: Optional[str] = None
    production_portable_spl: List[str] = Field(default_factory=list)
    netspout_specific_spl: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    known_gaps: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def classify_queries(self):
        forbidden = ("netspout_run_id", "netspout_scenario_id", "netspout_phase")
        for query in self.production_portable_spl:
            if any(field in query for field in forbidden):
                raise ValueError(
                    "production-portable SPL cannot depend on NetSpout metadata"
                )
        return self


class ScenarioDefinition(StrictModel):
    scenario_id: str
    title: str
    domain: str
    category: str
    difficulty: str = "INTERMEDIATE"
    story: str
    technical_objective: str
    business_impact: str
    technologies: List[str]
    entities: List[str]
    relationships: List[str]
    zones: List[str]
    failure_or_attack_vector: str
    enterprise_state: Dict[str, str]
    timeline: List[TimelineTransition]
    state_transitions: List[str]
    telemetry_sources: List[str] = Field(default_factory=list)
    native_transports: List[str] = Field(default_factory=list)
    source_contracts: List[str] = Field(default_factory=list)
    product_packs: List[str] = Field(default_factory=list)
    splunk_integrations: List[str] = Field(default_factory=list)
    sourcetypes: List[str] = Field(default_factory=list)
    cim_relationships: Dict[str, CimState] = Field(default_factory=dict)
    evidence_references: List[str] = Field(default_factory=list)
    investigation_pack: InvestigationPackRef
    troubleshooting_pack: TroubleshootingPackRef
    production_portability: ProductionPortability
    maturity: ScenarioMaturity
    validation_state: ValidationState
    research_gaps: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    runtime_scenario_id: Optional[str] = None
    execution_enabled: bool = False
    shared_state: bool = False
    guided_experience: bool = False
    topology_available: bool = False
    replay_supported: bool = False
    format_validation: List[str] = Field(default_factory=list)
    runtime_validation: List[str] = Field(default_factory=list)
    splunk_validation: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_maturity(self):
        concept = all(
            (
                self.title,
                self.domain,
                self.category,
                self.story,
                self.technical_objective,
                self.business_impact,
                self.failure_or_attack_vector,
                self.technologies,
                self.entities,
                self.zones,
                self.timeline,
                self.state_transitions,
            )
        )
        if not concept:
            raise ValueError("CANDIDATE gate requires a complete meaningful concept")

        ordered = {
            ScenarioMaturity.CANDIDATE: 0,
            ScenarioMaturity.RESEARCHED: 1,
            ScenarioMaturity.CONTRACTED: 2,
            ScenarioMaturity.FORMAT_VALIDATED: 3,
            ScenarioMaturity.RUNTIME_VALIDATED: 4,
            ScenarioMaturity.SPLUNK_VALIDATED: 5,
            ScenarioMaturity.GOLDEN: 6,
        }
        level = ordered.get(self.maturity)
        if level is not None and level >= 1:
            if not self.evidence_references or not self.telemetry_sources:
                raise ValueError("RESEARCHED gate requires evidence and telemetry candidates")
        if level is not None and level >= 2:
            if not (
                self.source_contracts
                and self.product_packs
                and self.native_transports
            ):
                raise ValueError("CONTRACTED gate requires contracts, Packs, and transport")
        if level is not None and level >= 3 and not self.format_validation:
            raise ValueError("FORMAT_VALIDATED gate requires structural validation")
        if level is not None and level >= 4 and not self.runtime_validation:
            raise ValueError("RUNTIME_VALIDATED gate requires runtime evidence")
        if level is not None and level >= 5 and not self.splunk_validation:
            raise ValueError("SPLUNK_VALIDATED gate requires fresh Splunk evidence")
        if level is not None and level >= 6:
            golden = (
                self.execution_enabled
                and self.shared_state
                and self.guided_experience
                and self.topology_available
                and self.replay_supported
                and self.investigation_pack.recipe_ids
                and self.investigation_pack.expected_findings
                and self.troubleshooting_pack.operation_ids
                and self.production_portability.guide_id
            )
            if not golden:
                raise ValueError("GOLDEN gate requires the complete guided evidence chain")
        if self.maturity in {
            ScenarioMaturity.RESEARCH_REQUIRED,
            ScenarioMaturity.BLOCKED,
        } and not self.research_gaps:
            raise ValueError("blocked maturity requires explicit research gaps")
        if self.maturity == ScenarioMaturity.UNSUPPORTED and not self.limitations:
            raise ValueError("UNSUPPORTED requires a reason")
        if self.execution_enabled and self.maturity not in {
            ScenarioMaturity.RUNTIME_VALIDATED,
            ScenarioMaturity.SPLUNK_VALIDATED,
            ScenarioMaturity.GOLDEN,
        }:
            raise ValueError("execution is disabled below RUNTIME_VALIDATED")
        return self


class ResearchItem(StrictModel):
    research_id: str
    scenario_id: str
    product: str
    source: str
    missing_claim: str
    required_evidence_type: str
    blocking_gate: str
    priority: str
    status: str


class SharedAsset(StrictModel):
    asset_id: str
    asset_type: str
    scenario_ids: List[str]
    evidence_ids: List[str] = Field(default_factory=list)


class ScenarioFactoryCatalog(StrictModel):
    schema_version: str
    catalog_version: str
    vendor_id: str
    independence_notice: str
    domain_targets: Dict[str, int]
    scenarios: List[ScenarioDefinition]
    research_queue: List[ResearchItem]
    shared_assets: List[SharedAsset] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_catalog(self):
        ids = [item.scenario_id for item in self.scenarios]
        if len(ids) != 100 or len(set(ids)) != 100:
            raise ValueError("Cisco scenario factory requires exactly 100 unique IDs")
        actual = Counter(item.domain for item in self.scenarios)
        if actual != Counter(self.domain_targets):
            raise ValueError(
                "scenario domain distribution does not match declared targets"
            )
        if set(actual.values()) != {20}:
            raise ValueError("each Cisco 100 domain must contain exactly 20 scenarios")
        queue_ids = {item.scenario_id for item in self.research_queue}
        scenario_ids = set(ids)
        if not queue_ids.issubset(scenario_ids):
            raise ValueError("research queue references an unknown scenario")
        for scenario in self.scenarios:
            if scenario.maturity == ScenarioMaturity.RESEARCH_REQUIRED:
                if scenario.scenario_id not in queue_ids:
                    raise ValueError(
                        f"{scenario.scenario_id} requires an actionable research item"
                    )
        for asset in self.shared_assets:
            if not set(asset.scenario_ids).issubset(scenario_ids):
                raise ValueError(f"{asset.asset_id} references an unknown scenario")
            if len(asset.scenario_ids) < 2:
                raise ValueError("shared assets must prove cross-scenario reuse")
        self._check_contract_consistency()
        return self

    def _check_contract_consistency(self) -> None:
        observed: Dict[str, Set[tuple]] = defaultdict(set)
        for scenario in self.scenarios:
            for contract in scenario.source_contracts:
                observed[contract].add(
                    (
                        tuple(sorted(scenario.native_transports)),
                        tuple(sorted(scenario.sourcetypes)),
                        tuple(sorted(scenario.splunk_integrations)),
                        tuple(sorted(scenario.cim_relationships.items())),
                    )
                )
        conflicts = sorted(key for key, values in observed.items() if len(values) > 1)
        if conflicts:
            raise ValueError(
                "cross-scenario contract contradiction: {}".format(
                    ", ".join(conflicts)
                )
            )

    def summary(self) -> Dict[str, Any]:
        maturity = Counter(item.maturity.value for item in self.scenarios)
        domains = Counter(item.domain for item in self.scenarios)
        products = {tech for item in self.scenarios for tech in item.technologies}
        source_contracts = {
            contract for item in self.scenarios for contract in item.source_contracts
        }
        protocols = {
            transport for item in self.scenarios for transport in item.native_transports
        }
        integrations = {
            integration
            for item in self.scenarios
            for integration in item.splunk_integrations
        }
        return {
            "scenario_definitions": len(self.scenarios),
            "domains": dict(sorted(domains.items())),
            "maturity": {
                value.value: maturity.get(value.value, 0)
                for value in ScenarioMaturity
            },
            "products_represented": len(products),
            "source_contracts": len(source_contracts),
            "native_protocols": len(protocols),
            "verified_splunk_integrations": len(integrations),
        }

    def evidence_debt(self) -> Dict[str, int]:
        return {
            "missing_native_contract": sum(
                not item.source_contracts for item in self.scenarios
            ),
            "missing_splunk_mapping": sum(
                not item.splunk_integrations for item in self.scenarios
            ),
            "runtime_blocked": sum(
                not item.runtime_validation for item in self.scenarios
            ),
            "cim_not_established": sum(
                not item.cim_relationships
                or any(
                    state == CimState.NOT_ESTABLISHED
                    for state in item.cim_relationships.values()
                )
                for item in self.scenarios
            ),
            "provenance_blocked": sum(
                "provenance" in " ".join(item.research_gaps).lower()
                for item in self.scenarios
            ),
            "licensing_blocked": sum(
                "licens" in " ".join(item.research_gaps).lower()
                for item in self.scenarios
            ),
        }


def _apply_scenario_promotions(
    catalog_payload: Dict[str, Any], promotion_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Overlay reviewed maturity evidence without rewriting the 100 definitions."""
    promoted = {
        item["scenario_id"]: item
        for item in promotion_payload.get("promotions", [])
    }
    known_ids = {
        item["scenario_id"] for item in catalog_payload.get("scenarios", [])
    }
    unknown_ids = sorted(set(promoted) - known_ids)
    if unknown_ids:
        raise ValueError(
            "Phase 8C promotion references unknown scenarios: {}".format(
                ", ".join(unknown_ids)
            )
        )
    for scenario in catalog_payload.get("scenarios", []):
        overlay = promoted.get(scenario["scenario_id"])
        if overlay:
            scenario.update(
                {key: value for key, value in overlay.items() if key != "scenario_id"}
            )
    catalog_payload["research_queue"] = [
        item
        for item in catalog_payload.get("research_queue", [])
        if item["scenario_id"] not in promoted
    ]
    for scenario_id, overlay in promoted.items():
        for index, gap in enumerate(overlay.get("research_gaps", []), start=1):
            catalog_payload["research_queue"].append(
                {
                    "research_id": "RQ-P8C-{}-{:02d}".format(
                        scenario_id, index
                    ),
                    "scenario_id": scenario_id,
                    "product": " / ".join(
                        next(
                            item["technologies"]
                            for item in catalog_payload["scenarios"]
                            if item["scenario_id"] == scenario_id
                        )
                    ),
                    "source": "PHASE8C_CURRENT_RUN",
                    "missing_claim": gap,
                    "required_evidence_type": (
                        "Guarded native receiver and authenticated Splunk evidence"
                    ),
                    "blocking_gate": "RUNTIME_VALIDATED",
                    "priority": "HIGH",
                    "status": "OPEN",
                }
            )
    catalog_payload["shared_assets"].extend(
        promotion_payload.get("shared_assets", [])
    )
    catalog_payload["catalog_version"] = promotion_payload["catalog_version"]
    return catalog_payload


class CiscoScenarioFactoryService:
    """Read, validate, filter, and trace scenario-definition dependencies."""

    def __init__(self, path: Optional[Path] = None):
        root = Path(__file__).resolve().parents[2]
        configured = os.environ.get("NETSPOUT_SCENARIO_FACTORY_CATALOG")
        catalog_path = path or (Path(configured) if configured else None)
        if catalog_path is None:
            packaged = (
                Path(__file__).resolve().parent
                / "catalog_data"
                / "cisco_100_scenarios.json"
            )
            catalog_path = (
                packaged
                if packaged.is_file()
                else root / "catalog" / "cisco_100_scenarios.json"
            )
        catalog_path = Path(catalog_path)
        with catalog_path.open("r", encoding="utf-8") as handle:
            catalog_payload = json.load(handle)
        promotion_path = catalog_path.with_name(
            "phase8c_scenario_promotions.json"
        )
        if promotion_path.is_file():
            with promotion_path.open("r", encoding="utf-8") as handle:
                promotion_payload = json.load(handle)
            catalog_payload = _apply_scenario_promotions(
                catalog_payload, promotion_payload
            )
        self.catalog = ScenarioFactoryCatalog.model_validate(catalog_payload)
        self._by_id = {item.scenario_id: item for item in self.catalog.scenarios}
        self._dependency_index = self._build_dependency_index()

    def _build_dependency_index(self) -> Dict[str, List[str]]:
        dependencies: Dict[str, Set[str]] = defaultdict(set)
        for scenario in self.catalog.scenarios:
            for value in (
                scenario.technologies
                + scenario.telemetry_sources
                + scenario.source_contracts
                + scenario.product_packs
                + scenario.investigation_pack.recipe_ids
            ):
                dependencies[value].add(scenario.scenario_id)
        return {key: sorted(value) for key, value in dependencies.items()}

    def view(
        self,
        *,
        domain: Optional[str] = None,
        product: Optional[str] = None,
        technology: Optional[str] = None,
        telemetry_source: Optional[str] = None,
        protocol: Optional[str] = None,
        integration: Optional[str] = None,
        maturity: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> Dict[str, Any]:
        start = perf_counter()
        scenarios = list(self.catalog.scenarios)
        predicates = (
            (domain, lambda item, value: item.domain == value),
            (product, lambda item, value: value in item.technologies),
            (technology, lambda item, value: value in item.technologies),
            (telemetry_source, lambda item, value: value in item.telemetry_sources),
            (protocol, lambda item, value: value in item.native_transports),
            (integration, lambda item, value: value in item.splunk_integrations),
            (maturity, lambda item, value: item.maturity.value == value),
            (category, lambda item, value: item.category == value),
            (difficulty, lambda item, value: item.difficulty == value),
        )
        for selected, predicate in predicates:
            if selected:
                scenarios = [item for item in scenarios if predicate(item, selected)]
        elapsed_ms = (perf_counter() - start) * 1000
        return {
            "schema_version": self.catalog.schema_version,
            "catalog_version": self.catalog.catalog_version,
            "vendor_id": self.catalog.vendor_id,
            "independence_notice": self.catalog.independence_notice,
            "summary": self.catalog.summary(),
            "evidence_debt": self.catalog.evidence_debt(),
            "scenarios": [item.model_dump(mode="json") for item in scenarios],
            "research_queue": [
                item.model_dump(mode="json") for item in self.catalog.research_queue
            ],
            "shared_assets": [
                item.model_dump(mode="json") for item in self.catalog.shared_assets
            ],
            "filter_result_count": len(scenarios),
            "query_ms": round(elapsed_ms, 3),
        }

    def scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        scenario = self._by_id.get(scenario_id)
        if scenario is None:
            return None
        return {
            "scenario": scenario.model_dump(mode="json"),
            "research_queue": [
                item.model_dump(mode="json")
                for item in self.catalog.research_queue
                if item.scenario_id == scenario_id
            ],
            "dependencies": sorted(
                key
                for key, scenario_ids in self._dependency_index.items()
                if scenario_id in scenario_ids
            ),
        }

    def affected_scenarios(self, dependency_id: str) -> Dict[str, Any]:
        scenarios = self._dependency_index.get(dependency_id, [])
        affected = [self._by_id[scenario_id] for scenario_id in scenarios]
        return {
            "dependency_id": dependency_id,
            "affected_scenario_ids": scenarios,
            "affected_product_packs": sorted(
                {pack for item in affected for pack in item.product_packs}
            ),
            "affected_investigation_packs": sorted(
                {
                    recipe
                    for item in affected
                    for recipe in item.investigation_pack.recipe_ids
                }
            ),
            "required_revalidation": (
                ["STATIC", "FORMAT", "RUNTIME", "SPLUNK", "GUIDED_LAB"]
                if scenarios
                else []
            ),
            "revalidation_required": bool(scenarios),
        }

    def validate_promotion(
        self, scenario_id: str, target: ScenarioMaturity
    ) -> Dict[str, Any]:
        """Enforce one evidence gate at a time; this never mutates catalog state."""
        scenario = self._by_id.get(scenario_id)
        if scenario is None:
            raise KeyError(scenario_id)
        lifecycle = [
            ScenarioMaturity.CANDIDATE,
            ScenarioMaturity.RESEARCHED,
            ScenarioMaturity.CONTRACTED,
            ScenarioMaturity.FORMAT_VALIDATED,
            ScenarioMaturity.RUNTIME_VALIDATED,
            ScenarioMaturity.SPLUNK_VALIDATED,
            ScenarioMaturity.GOLDEN,
        ]
        if scenario.maturity not in lifecycle or target not in lifecycle:
            raise ValueError(
                f"{scenario.maturity.value} is a blocking classification, not a promotable gate"
            )
        current_index = lifecycle.index(scenario.maturity)
        expected = (
            lifecycle[current_index + 1]
            if current_index + 1 < len(lifecycle)
            else None
        )
        if target != expected:
            raise ValueError(
                f"invalid maturity promotion {scenario.maturity.value} -> {target.value}; "
                "promotion must advance exactly one evidence gate"
            )
        candidate = scenario.model_copy(update={"maturity": target})
        ScenarioDefinition.model_validate(candidate.model_dump(mode="json"))
        return {
            "scenario_id": scenario_id,
            "from": scenario.maturity.value,
            "to": target.value,
            "allowed": True,
        }

    def execution_decision(self, scenario_id: str) -> Dict[str, Any]:
        """Fail closed unless live runtime validation permits delegated execution."""
        scenario = self._by_id.get(scenario_id)
        if scenario is None:
            raise KeyError(scenario_id)
        if not scenario.execution_enabled or not scenario.runtime_scenario_id:
            missing = scenario.research_gaps or [
                "Runtime validation and an executable Scenario Pack are not established"
            ]
            raise ValueError(
                f"{scenario_id} generation blocked at {scenario.maturity.value}: "
                f"{'; '.join(missing)}. No fallback event, sourcetype, integration, "
                "or CIM relationship will be generated."
            )
        return {
            "scenario_id": scenario_id,
            "runtime_scenario_id": scenario.runtime_scenario_id,
            "delegation": "GUIDED_SCENARIO_EXPERIENCE",
        }

    def coverage_matrix(self) -> List[Dict[str, Any]]:
        return [
            {
                "scenario_id": item.scenario_id,
                "domain": item.domain,
                "products": item.technologies,
                "telemetry_sources": item.telemetry_sources,
                "contract": bool(item.source_contracts),
                "runtime": bool(item.runtime_validation),
                "splunk": bool(item.splunk_validation),
                "cim": sorted(
                    {state.value for state in item.cim_relationships.values()}
                )
                or [CimState.NOT_ESTABLISHED.value],
                "golden": item.maturity == ScenarioMaturity.GOLDEN,
            }
            for item in self.catalog.scenarios
        ]
