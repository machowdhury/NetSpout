"""Scenario-aware dashboard contracts, recipes, validation, and export.

Dashboard Packs reference authoritative Scenario, Source, Investigation, and
Industry contracts. They never alter native telemetry or create a second
entity graph.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Set

from pydantic import Field, model_validator

from netspout_core.catalog_contracts import StrictModel


class DashboardMaturity(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    GENERATED = "GENERATED"
    SPL_VALIDATED = "SPL_VALIDATED"
    DATA_VALIDATED = "DATA_VALIDATED"
    VISUALLY_VALIDATED = "VISUALLY_VALIDATED"
    DASHBOARD_READY = "DASHBOARD_READY"


class DashboardEligibilityState(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"
    DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"
    UNSUPPORTED = "UNSUPPORTED"


class VisualizationCompatibility(str, Enum):
    VERIFIED = "VERIFIED"
    DOCUMENTED = "DOCUMENTED"
    NOT_VERIFIED = "NOT_VERIFIED"
    INCOMPATIBLE = "INCOMPATIBLE"


class DashboardPerspective(str, Enum):
    NOC = "NOC"
    ENGINEER = "ENGINEER"
    EVIDENCE = "EVIDENCE"


class DashboardDesignReference(StrictModel):
    title: str
    publisher: str
    reference: str
    verification_state: str


class VisualizationDefinition(StrictModel):
    visualization_id: str
    display_name: str
    engine: str
    type_name: str
    required_shape: str
    dependency: Optional[str] = None
    compatibility: VisualizationCompatibility
    fallback_id: Optional[str] = None


class DashboardDrilldown(StrictModel):
    token: str
    field: str
    semantics: str


class DashboardRecipe(StrictModel):
    recipe_id: str
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    family: str
    purpose: str
    selectors: List[str]
    required_fields: List[str]
    optional_fields: List[str]
    visualization_ids: List[str]
    query_template: Optional[str] = None
    expected_shape: Dict[str, str]
    drilldowns: List[DashboardDrilldown]
    evidence_requirements: List[str]
    portability: str
    validation_requirements: List[str]

    @model_validator(mode="after")
    def enforce_bounded_search(self):
        if self.query_template:
            required_tokens = ("{index}", "{sourcetype_filter}", "{run_id}")
            if any(token not in self.query_template for token in required_tokens):
                raise ValueError(
                    "dashboard searches require index, source, and run placeholders"
                )
            lowered = self.query_template.lower()
            if "earliest=" not in lowered or "latest=" not in lowered:
                raise ValueError("dashboard searches require a bounded time range")
            if "| join" in lowered:
                raise ValueError("dashboard recipes cannot use unbounded joins")
        return self


class DashboardRecipeRegistry(StrictModel):
    schema_version: str
    registry_version: str
    design_reference: DashboardDesignReference
    visualizations: List[VisualizationDefinition]
    recipes: List[DashboardRecipe]

    @model_validator(mode="after")
    def validate_registry(self):
        visualization_ids = [item.visualization_id for item in self.visualizations]
        recipe_ids = [item.recipe_id for item in self.recipes]
        if len(visualization_ids) != len(set(visualization_ids)):
            raise ValueError("duplicate visualization ID")
        if len(recipe_ids) != len(set(recipe_ids)):
            raise ValueError("duplicate dashboard recipe ID")
        known = set(visualization_ids)
        for visualization in self.visualizations:
            if visualization.fallback_id and visualization.fallback_id not in known:
                raise ValueError("visualization fallback is not registered")
        for recipe in self.recipes:
            missing = sorted(set(recipe.visualization_ids) - known)
            if missing:
                raise ValueError(
                    "{} references unknown visualizations: {}".format(
                        recipe.recipe_id, ", ".join(missing)
                    )
                )
        return self


class DashboardEligibility(StrictModel):
    dashboard_id: str
    scenario_id: str
    runtime_scenario_id: str
    title: str
    domain: str
    category: str
    industry_id: Optional[str] = None
    scenario_maturity: str
    dashboard_maturity: DashboardMaturity = DashboardMaturity.NOT_STARTED
    state: DashboardEligibilityState
    reasons: List[str]
    source_ids: List[str]
    investigation_recipe_ids: List[str]
    recipe_ids: List[str] = Field(default_factory=list)


class DashboardPanel(StrictModel):
    panel_id: str
    recipe_id: str
    title: str
    purpose: str
    perspective: DashboardPerspective
    executable: bool
    query: Optional[str] = None
    portability: str
    required_fields: List[str]
    optional_fields: List[str]
    expected_shape: Dict[str, str]
    visualization_id: str
    requested_visualization_id: str
    dependency_state: str
    drilldowns: List[DashboardDrilldown]
    evidence_requirements: List[str]


class DashboardValidationEvidence(StrictModel):
    evidence_id: str
    dashboard_id: str
    scenario_id: str
    run_id: Optional[str]
    recorded_at: str
    maturity: DashboardMaturity
    spl_validated: bool
    data_validated: bool
    visually_validated: bool = False
    export_validated: bool = False
    observed_fields: List[str] = Field(default_factory=list)
    panel_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    failures: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class DashboardPack(StrictModel):
    schema_version: str = "1.0.0"
    dashboard_id: str
    dashboard_version: str = "1.0.0"
    title: str
    description: str
    scenario_id: str
    runtime_scenario_id: str
    scenario_version: str
    run_id: Optional[str]
    domain: str
    category: str
    industry_id: Optional[str]
    source_contracts: List[Dict[str, Any]]
    splunk_contracts: List[Dict[str, Any]]
    investigation_recipe_ids: List[str]
    detection_pack_ids: List[str]
    entity_graph: Dict[str, Any]
    topology_ref: str
    telemetry_manifest: List[Dict[str, Any]]
    observed_fields: List[str]
    panels: List[DashboardPanel]
    perspectives: Dict[str, List[str]]
    maturity: DashboardMaturity
    validation_evidence: List[DashboardValidationEvidence]
    cim_status: str
    export_compatibility: str
    limitations: List[str]


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_dict(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


class DashboardEvidenceStore:
    """Persist dashboard validation independently from scenario maturity."""

    def __init__(self, storage_dir: Optional[str] = None):
        configured = storage_dir or os.environ.get("NETSPOUT_DASHBOARD_EVIDENCE_DIR")
        self.storage_dir = Path(
            configured
            or Path(tempfile.gettempdir()) / "netspout-dashboard-validation"
        ).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, evidence: DashboardValidationEvidence) -> None:
        path = self.storage_dir / "{}.json".format(evidence.evidence_id)
        path.write_text(
            json.dumps(evidence.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )

    def list_for(self, dashboard_id: str) -> List[DashboardValidationEvidence]:
        records: List[DashboardValidationEvidence] = []
        for path in sorted(self.storage_dir.glob("*.json")):
            try:
                record = DashboardValidationEvidence.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError):
                continue
            if record.dashboard_id == dashboard_id:
                records.append(record)
        records.sort(key=lambda item: item.recorded_at)
        return records


class DashboardRecipeService:
    """Discover eligible scenarios and generate dashboard packs generically."""

    RUNTIME_SOURCETYPES = {
        "ietf-syslog-rfc5424": "netspout:rfc5424",
        "ietf-snmpv2c-ifmib": "netspout:snmp:*",
        "openconfig-gnmi-interfaces": "netspout:gnmi:event",
        "ietf-netflow-v9": "netflow:collector",
        "ietf-ipfix": "netflow:collector",
        "ietf-dns-rfc1035": "netspout:dns:wire",
    }

    def __init__(
        self,
        specification: Dict[str, Any],
        catalog: Any,
        pack_registry: Any,
        industry_registry: Optional[Any] = None,
        cisco_scenarios: Optional[Iterable[Any]] = None,
        evidence_dir: Optional[str] = None,
    ):
        self.registry = DashboardRecipeRegistry.model_validate(specification)
        self.catalog = catalog
        self.pack_registry = pack_registry
        self.industry_registry = industry_registry
        self.cisco_scenarios = list(cisco_scenarios or [])
        self.evidence_store = DashboardEvidenceStore(evidence_dir)
        self._visualizations = {
            item.visualization_id: item for item in self.registry.visualizations
        }
        self._recipes = {item.recipe_id: item for item in self.registry.recipes}
        self._contexts = self._discover_contexts()

    def _pack_scenarios(self) -> Dict[str, Dict[str, Any]]:
        scenarios: Dict[str, Dict[str, Any]] = {}
        for pack in self.pack_registry.packs:
            for scenario in pack.scenarios:
                scenarios[scenario.scenario_id] = _as_dict(scenario)
        return scenarios

    def _discover_contexts(self) -> Dict[str, Dict[str, Any]]:
        scenarios = self._pack_scenarios()
        cisco_by_id = {
            item.scenario_id: _as_dict(item) for item in self.cisco_scenarios
        }
        contexts: Dict[str, Dict[str, Any]] = {}
        for scenario_id, scenario in scenarios.items():
            cisco = cisco_by_id.get(scenario_id)
            maturity = (
                cisco.get("maturity")
                if cisco
                else scenario.get("scenario_maturity") or scenario.get("maturity")
            )
            contexts["scenario-{}".format(scenario_id.lower())] = {
                "dashboard_id": "scenario-{}".format(scenario_id.lower()),
                "scenario_id": scenario_id,
                "runtime_scenario_id": scenario_id,
                "title": scenario.get("title", scenario_id),
                "domain": scenario.get("domain") or "Unclassified",
                "category": scenario.get("category") or "UNCLASSIFIED",
                "industry_id": None,
                "scenario_maturity": str(maturity or "NOT_ESTABLISHED"),
                "runnable": bool(scenario.get("runnable", True)),
                "source_ids": list(scenario.get("source_ids", [])),
                "investigation_recipe_ids": list(
                    scenario.get("investigation_recipe_ids", [])
                ),
                "nodes": list(scenario.get("nodes", [])),
                "relationships": list(scenario.get("relationships", [])),
                "timeline": list(scenario.get("timeline", [])),
                "detection_pack_ids": [
                    item.get("detection_id")
                    for item in scenario.get("detection_validation", [])
                    if item.get("detection_id")
                ],
                "declared_fields": sorted(
                    {
                        field
                        for item in scenario.get("kpi_definitions", [])
                        for field in item.get("required_fields", [])
                    }
                    | {
                        field
                        for item in scenario.get("detection_validation", [])
                        for field in item.get("required_fields", [])
                    }
                ),
                "limitations": list(scenario.get("known_blind_spots", [])),
            }

        for scenario_id, cisco in cisco_by_id.items():
            if cisco.get("maturity") != "GOLDEN":
                continue
            runtime_scenario_id = cisco.get("runtime_scenario_id") or scenario_id
            runtime = scenarios.get(runtime_scenario_id, {})
            dashboard_id = "scenario-{}".format(scenario_id.lower())
            contexts[dashboard_id] = {
                "dashboard_id": dashboard_id,
                "scenario_id": scenario_id,
                "runtime_scenario_id": runtime_scenario_id,
                "title": cisco.get("title", scenario_id),
                "domain": cisco.get("domain", "Cisco"),
                "category": cisco.get("category", "CISCO_GOLDEN"),
                "industry_id": None,
                "scenario_maturity": "GOLDEN",
                "runnable": bool(cisco.get("execution_enabled")),
                "source_ids": list(cisco.get("telemetry_sources", [])),
                "investigation_recipe_ids": list(
                    cisco.get("investigation_pack", {}).get("recipe_ids", [])
                    or runtime.get("investigation_recipe_ids", [])
                ),
                "nodes": list(runtime.get("nodes", [])),
                "relationships": list(runtime.get("relationships", [])),
                "timeline": list(runtime.get("timeline", [])),
                "detection_pack_ids": [],
                "declared_fields": [],
                "limitations": list(cisco.get("limitations", [])),
            }

        if self.industry_registry is not None:
            for industry in self.industry_registry.industries:
                data = _as_dict(industry)
                for environment in data.get("environments", []):
                    scenario_id = environment["default_scenario_id"]
                    dashboard_id = "industry-{}".format(data["industry_id"])
                    contexts[dashboard_id] = {
                        "dashboard_id": dashboard_id,
                        "scenario_id": scenario_id,
                        "runtime_scenario_id": scenario_id,
                        "title": "{} — {}".format(data["name"], environment["name"]),
                        "domain": "Industry",
                        "category": "INDUSTRY_REFERENCE",
                        "industry_id": data["industry_id"],
                        "scenario_maturity": data["maturity"],
                        "runnable": True,
                        "source_ids": list(environment["telemetry_source_ids"]),
                        "investigation_recipe_ids": list(
                            scenarios.get(scenario_id, {}).get(
                                "investigation_recipe_ids", []
                            )
                        ),
                        "nodes": [
                            {
                                "node_id": item["entity_id"],
                                "label": item["label"],
                                "role": item["entity_kind"],
                                "zone_id": item["zone_id"],
                                "source_ids": (
                                    environment["telemetry_source_ids"]
                                    if item.get("attributes", {}).get("view")
                                    == "technical"
                                    else []
                                ),
                            }
                            for item in data["entities"]
                            if item["entity_id"] in environment["entity_ids"]
                        ],
                        "relationships": [
                            {
                                "relationship_id": item["dependency_id"],
                                "source_node_id": item["source_entity_id"],
                                "target_node_id": item["target_entity_id"],
                                "relationship_type": item["relationship_type"],
                                "purpose": item["assumption"],
                            }
                            for item in data["dependencies"]
                            if item["dependency_id"] in environment["dependency_ids"]
                        ],
                        "timeline": list(
                            scenarios.get(scenario_id, {}).get("timeline", [])
                        ),
                        "detection_pack_ids": [],
                        "declared_fields": [],
                        "business_impacts": list(data.get("business_impacts", [])),
                        "limitations": [
                            exclusion
                            for impact in data.get("business_impacts", [])
                            for exclusion in impact.get("exclusions", [])
                        ],
                    }
        return contexts

    def _selectors(self, context: Dict[str, Any]) -> Set[str]:
        scenario_id = context["scenario_id"].upper()
        source_ids = set(context["source_ids"])
        domain = context["domain"].lower()
        category = context["category"].lower()
        selectors = {"infrastructure"}
        if len(source_ids) > 1:
            selectors.add("multi_source")
        if context.get("industry_id"):
            selectors.update({"industry", "application"})
        if (
            "routing" in category
            or "service provider" in domain
            or scenario_id in {"C100-SP-001", "C100-CRI-002"}
        ):
            selectors.add("routing")
        if context.get("industry_id") == "financial-services" or scenario_id == "C100-CRI-002":
            selectors.add("wan")
        if "data center" in domain or scenario_id == "C100-DC-001":
            selectors.add("data_center")
        if "ietf-ipfix" in source_ids or "ietf-netflow-v9" in source_ids:
            selectors.update({"flow", "traffic"})
        if "ietf-dns-rfc1035" in source_ids:
            selectors.add("dns")
        if any(term in scenario_id for term in ("BEACON", "DNS-TUNNEL", "CROSS-SOURCE")):
            selectors.add("beaconing")
        if "INTERNAL-RECON" in scenario_id or "CROSS-SOURCE" in scenario_id:
            selectors.add("recon")
        if "security" in domain or scenario_id.startswith("SEC-") or scenario_id == "C100-SEC-001":
            selectors.add("security")
        if "cross" in domain or "CROSS" in scenario_id or len(source_ids) > 1:
            selectors.add("cross_domain")
        return selectors

    def _eligible(self, context: Dict[str, Any]) -> DashboardEligibility:
        reasons: List[str] = []
        maturity = context["scenario_maturity"]
        mature = maturity in {"GOLDEN", "SPLUNK_VALIDATED"}
        if not mature:
            reasons.append(
                "scenario maturity {} does not establish dashboard execution".format(
                    maturity
                )
            )
        if not context["runnable"]:
            reasons.append("scenario is not executable")
        if not context["source_ids"]:
            reasons.append("scenario has no Source Contracts")
        if not context["investigation_recipe_ids"]:
            reasons.append("scenario has no Investigation Pack reference")
        if not context["nodes"] or not context["relationships"]:
            reasons.append("scenario has no reusable entity graph")
        state = (
            DashboardEligibilityState.ELIGIBLE
            if not reasons
            else DashboardEligibilityState.RESEARCH_REQUIRED
        )
        recipe_ids = [
            item.recipe_id
            for item in self._matching_recipes(context)
        ] if state == DashboardEligibilityState.ELIGIBLE else []
        evidence = self.evidence_store.list_for(context["dashboard_id"])
        return DashboardEligibility(
            dashboard_id=context["dashboard_id"],
            scenario_id=context["scenario_id"],
            runtime_scenario_id=context["runtime_scenario_id"],
            title=context["title"],
            domain=context["domain"],
            category=context["category"],
            industry_id=context.get("industry_id"),
            scenario_maturity=maturity,
            dashboard_maturity=(
                evidence[-1].maturity if evidence else DashboardMaturity.NOT_STARTED
            ),
            state=state,
            reasons=reasons or ["verified mature scenario metadata is complete"],
            source_ids=context["source_ids"],
            investigation_recipe_ids=context["investigation_recipe_ids"],
            recipe_ids=recipe_ids,
        )

    def _matching_recipes(self, context: Dict[str, Any]) -> List[DashboardRecipe]:
        selectors = self._selectors(context)
        return [
            item
            for item in self.registry.recipes
            if "*" in item.selectors or selectors.intersection(item.selectors)
        ]

    def catalog_summary(self) -> Dict[str, Any]:
        entries = [
            self._eligible(context).model_dump(mode="json")
            for context in self._contexts.values()
        ]
        return {
            "schema_version": self.registry.schema_version,
            "registry_version": self.registry.registry_version,
            "design_reference": self.registry.design_reference.model_dump(mode="json"),
            "recipes": [
                item.model_dump(mode="json") for item in self.registry.recipes
            ],
            "visualizations": [
                item.model_dump(mode="json") for item in self.registry.visualizations
            ],
            "dashboards": entries,
            "eligible_count": sum(
                item["state"] == DashboardEligibilityState.ELIGIBLE.value
                for item in entries
            ),
        }

    def eligibility(self, dashboard_id: str) -> Optional[DashboardEligibility]:
        context = self._contexts.get(dashboard_id)
        return self._eligible(context) if context else None

    def _source_contract(self, source_id: str) -> Dict[str, Any]:
        source = self.catalog.get_telemetry_source(source_id) or {}
        if not source:
            for pack in self.pack_registry.packs:
                for entry in pack.sources:
                    if entry.source.source_id == source_id:
                        source = entry.source.model_dump(mode="json")
                        break
        return source

    def _source_metadata(self, source_ids: List[str]) -> Dict[str, Any]:
        source_contracts = []
        splunk_contracts = []
        manifest = []
        sourcetypes = []
        for source_id in source_ids:
            source = self._source_contract(source_id)
            native = source.get("native_contract", {})
            splunk = source.get("splunk_contract", {})
            netspout = source.get("netspout_contract", {})
            source_contracts.append(
                {
                    "source_id": source_id,
                    "native_contract_id": native.get("contract_id"),
                    "netspout_contract_id": netspout.get("contract_id"),
                    "verification_state": native.get("verification_state"),
                    "preserve_native_raw": True,
                }
            )
            declared_sourcetypes = [
                item.get("name")
                for item in splunk.get("sourcetypes", [])
                if item.get("name")
            ]
            if source_id in self.RUNTIME_SOURCETYPES:
                declared_sourcetypes = [self.RUNTIME_SOURCETYPES[source_id]]
            sourcetypes.extend(declared_sourcetypes)
            splunk_contracts.append(
                {
                    "source_id": source_id,
                    "splunk_contract_id": splunk.get("contract_id"),
                    "sourcetypes": declared_sourcetypes,
                    "cim_mappings": splunk.get("cim_mappings", []),
                    "verification_state": splunk.get("verification_state"),
                }
            )
            manifest.append(
                {
                    "source_id": source_id,
                    "sourcetypes": declared_sourcetypes,
                    "native_contract_id": native.get("contract_id"),
                    "splunk_contract_id": splunk.get("contract_id"),
                    "netspout_contract_id": netspout.get("contract_id"),
                }
            )
        return {
            "source_contracts": source_contracts,
            "splunk_contracts": splunk_contracts,
            "telemetry_manifest": manifest,
            "sourcetypes": sorted(set(sourcetypes)),
        }

    def _resolve_visualization(self, recipe: DashboardRecipe) -> Dict[str, str]:
        requested = self._visualizations[recipe.visualization_ids[0]]
        selected = requested
        state = requested.compatibility.value
        if requested.compatibility in {
            VisualizationCompatibility.NOT_VERIFIED,
            VisualizationCompatibility.INCOMPATIBLE,
        }:
            if not requested.fallback_id:
                raise ValueError(
                    "{} visualization dependency is unavailable".format(
                        requested.visualization_id
                    )
                )
            selected = self._visualizations[requested.fallback_id]
            state = "FALLBACK:{}".format(requested.compatibility.value)
        return {
            "requested": requested.visualization_id,
            "selected": selected.visualization_id,
            "state": state,
        }

    def generate(
        self,
        dashboard_id: str,
        run_id: Optional[str] = None,
        index: str = "idx_network_ops",
    ) -> DashboardPack:
        context = self._contexts.get(dashboard_id)
        if context is None:
            raise ValueError("unknown dashboard")
        eligibility = self._eligible(context)
        if eligibility.state != DashboardEligibilityState.ELIGIBLE:
            raise ValueError(
                "dashboard is not eligible: {}".format("; ".join(eligibility.reasons))
            )
        if not _SAFE_IDENTIFIER.fullmatch(index):
            raise ValueError("unsafe Splunk index")
        if run_id is not None and not _SAFE_IDENTIFIER.fullmatch(run_id):
            raise ValueError("unsafe run ID")

        metadata = self._source_metadata(context["source_ids"])
        source_filter = "({})".format(
            " OR ".join(
                'sourcetype="{}"'.format(item)
                for item in metadata["sourcetypes"]
            )
        )
        panels = []
        perspective_map = {
            DashboardPerspective.NOC.value: [],
            DashboardPerspective.ENGINEER.value: [],
            DashboardPerspective.EVIDENCE.value: [],
        }
        recipes = self._matching_recipes(context)
        for position, recipe in enumerate(recipes):
            visualization = self._resolve_visualization(recipe)
            query = None
            if recipe.query_template and run_id:
                query = recipe.query_template.format(
                    index=index,
                    sourcetype_filter=source_filter,
                    run_id=run_id,
                )
            perspective = (
                DashboardPerspective.NOC
                if position % 3 == 0
                else DashboardPerspective.ENGINEER
                if position % 3 == 1
                else DashboardPerspective.EVIDENCE
            )
            if recipe.recipe_id in {
                "dashboard-evidence-chain",
                "dashboard-source-detail",
                "dashboard-investigation-workbench",
            }:
                perspective = DashboardPerspective.EVIDENCE
            panel = DashboardPanel(
                panel_id="panel-{}".format(recipe.recipe_id.removeprefix("dashboard-")),
                recipe_id=recipe.recipe_id,
                title=recipe.family,
                purpose=recipe.purpose,
                perspective=perspective,
                executable=bool(recipe.query_template and run_id),
                query=query,
                portability=recipe.portability,
                required_fields=recipe.required_fields,
                optional_fields=recipe.optional_fields,
                expected_shape=recipe.expected_shape,
                visualization_id=visualization["selected"],
                requested_visualization_id=visualization["requested"],
                dependency_state=visualization["state"],
                drilldowns=recipe.drilldowns,
                evidence_requirements=recipe.evidence_requirements,
            )
            panels.append(panel)
            perspective_map[perspective.value].append(panel.panel_id)

        prior_evidence = self.evidence_store.list_for(dashboard_id)
        observed_fields = sorted(
            {
                field
                for evidence in prior_evidence
                if evidence.run_id == run_id
                for field in evidence.observed_fields
            }
        )
        maturity = (
            prior_evidence[-1].maturity
            if prior_evidence and prior_evidence[-1].run_id == run_id
            else DashboardMaturity.GENERATED
        )
        return DashboardPack(
            dashboard_id=dashboard_id,
            title="{} Dashboard".format(context["title"]),
            description=(
                "Scenario-aware dashboard generated from verified contracts. "
                "Unsupported fields and CIM mappings remain unclaimed."
            ),
            scenario_id=context["scenario_id"],
            runtime_scenario_id=context["runtime_scenario_id"],
            scenario_version="1.0.0",
            run_id=run_id,
            domain=context["domain"],
            category=context["category"],
            industry_id=context.get("industry_id"),
            source_contracts=metadata["source_contracts"],
            splunk_contracts=metadata["splunk_contracts"],
            investigation_recipe_ids=context["investigation_recipe_ids"],
            detection_pack_ids=context["detection_pack_ids"],
            entity_graph={
                "nodes": context["nodes"],
                "relationships": context["relationships"],
                "shared_with_scenario": True,
            },
            topology_ref="scenario:{}".format(context["runtime_scenario_id"]),
            telemetry_manifest=metadata["telemetry_manifest"],
            observed_fields=observed_fields,
            panels=panels,
            perspectives=perspective_map,
            maturity=maturity,
            validation_evidence=prior_evidence,
            cim_status="NOT_ESTABLISHED",
            export_compatibility="DASHBOARD_STUDIO_JSON_PREVIEW",
            limitations=context.get("limitations", [])
            + [
                "Dashboard maturity is independent from scenario maturity.",
                "CIM functionality is unavailable until independently established.",
            ],
        )

    def validate(
        self,
        pack: DashboardPack,
        panel_results: Dict[str, List[Dict[str, Any]]],
        evidence_refs: Optional[List[str]] = None,
        execution_failures: Optional[List[str]] = None,
    ) -> DashboardValidationEvidence:
        failures = list(execution_failures or [])
        observed_fields: Set[str] = set()
        summaries: Dict[str, Dict[str, Any]] = {}
        executable = [item for item in pack.panels if item.executable]
        if not executable:
            failures.append("dashboard has no run-scoped executable panels")
        for panel in executable:
            rows = panel_results.get(panel.panel_id)
            if rows is None:
                failures.append("{} has no SPL result".format(panel.panel_id))
                continue
            fields = {field for row in rows for field in row}
            observed_fields.update(fields)
            expected = set(panel.expected_shape)
            missing = sorted(expected - fields)
            if missing:
                failures.append(
                    "{} missing expected fields: {}".format(
                        panel.panel_id, ", ".join(missing)
                    )
                )
            summaries[panel.panel_id] = {
                "row_count": len(rows),
                "observed_fields": sorted(fields),
                "expected_fields": sorted(expected),
                "shape_valid": not missing,
            }
        spl_validated = all(
            panel.panel_id in panel_results for panel in executable
        ) and bool(executable)
        data_validated = spl_validated and not failures
        maturity = (
            DashboardMaturity.DATA_VALIDATED
            if data_validated
            else DashboardMaturity.SPL_VALIDATED
            if spl_validated
            else DashboardMaturity.VALIDATION_FAILED
        )
        evidence = DashboardValidationEvidence(
            evidence_id="dashboard-validation-{}-{}".format(
                pack.dashboard_id,
                (pack.run_id or "design").replace(":", "-"),
            ),
            dashboard_id=pack.dashboard_id,
            scenario_id=pack.scenario_id,
            run_id=pack.run_id,
            recorded_at=_utc_now(),
            maturity=maturity,
            spl_validated=spl_validated,
            data_validated=data_validated,
            observed_fields=sorted(observed_fields),
            panel_results=summaries,
            failures=failures,
            evidence_refs=evidence_refs or [],
        )
        self.evidence_store.save(evidence)
        return evidence

    def mark_visual_validation(
        self,
        dashboard_id: str,
        run_id: str,
        evidence_ref: str,
        export_validated: bool,
    ) -> DashboardValidationEvidence:
        records = [
            item
            for item in self.evidence_store.list_for(dashboard_id)
            if item.run_id == run_id
        ]
        if not records or not records[-1].data_validated:
            raise ValueError("data validation is required before visual validation")
        evidence = records[-1].model_copy(deep=True)
        evidence.recorded_at = _utc_now()
        evidence.visually_validated = True
        evidence.export_validated = export_validated
        evidence.evidence_refs.append(evidence_ref)
        evidence.maturity = (
            DashboardMaturity.DASHBOARD_READY
            if export_validated
            else DashboardMaturity.VISUALLY_VALIDATED
        )
        self.evidence_store.save(evidence)
        return evidence

    def export_dashboard_studio(self, pack: DashboardPack) -> Dict[str, Any]:
        data_sources: Dict[str, Any] = {}
        visualizations: Dict[str, Any] = {}
        structure = []
        exported_panel_ids = []
        y = 0
        for index, panel in enumerate(pack.panels):
            visualization_id = "viz_{}".format(index + 1)
            exported_panel_ids.append(visualization_id)
            if panel.executable and panel.query:
                data_source_id = "ds_{}".format(index + 1)
                data_sources[data_source_id] = {
                    "type": "ds.search",
                    "name": panel.title,
                    "options": {
                        "query": panel.query,
                        "enableSmartSources": True,
                    },
                }
                visualization_type = self._visualizations[
                    panel.visualization_id
                ].type_name
                if not visualization_type.startswith("splunk."):
                    visualization_type = "splunk.table"
                visualizations[visualization_id] = {
                    "type": visualization_type,
                    "title": panel.title,
                    "description": panel.purpose,
                    "dataSources": {"primary": data_source_id},
                    "showProgressBar": False,
                    "showLastUpdated": True,
                }
            else:
                visualizations[visualization_id] = {
                    "type": "splunk.markdown",
                    "title": panel.title,
                    "options": {
                        "markdown": (
                            "**NetSpout context panel.** {} "
                            "This export does not fabricate a search-backed result."
                        ).format(panel.purpose)
                    },
                }
            structure.append(
                {
                    "item": visualization_id,
                    "type": "block",
                    "position": {
                        "x": 0 if index % 2 == 0 else 600,
                        "y": y,
                        "w": 580,
                        "h": 300,
                    },
                }
            )
            if index % 2 == 1:
                y += 320
        definition = {
            "title": pack.title,
            "description": pack.description,
            "inputs": {
                "input_global_time": {
                    "type": "input.timerange",
                    "title": "Global Time Range",
                    "options": {
                        "token": "global_time",
                        "defaultValue": "-15m,now",
                    },
                }
            },
            "defaults": {
                "dataSources": {
                    "ds.search": {
                        "options": {
                            "queryParameters": {
                                "earliest": "$global_time.earliest$",
                                "latest": "$global_time.latest$",
                            }
                        }
                    }
                }
            },
            "visualizations": visualizations,
            "dataSources": data_sources,
            "layout": {
                "globalInputs": ["input_global_time"],
                "layoutDefinitions": {
                    "layout_1": {
                        "type": "absolute",
                        "options": {
                            "display": "auto-scale",
                            "width": 1200,
                            "height": max(700, y + 340),
                        },
                        "structure": structure,
                    }
                },
                "tabs": {
                    "items": [
                        {"label": "Scenario", "layoutId": "layout_1"}
                    ]
                },
            },
            "expressions": {},
            "applicationProperties": {
                "hideEdit": False,
                "hideExport": False,
            },
        }
        validation = self.validate_export(definition, exported_panel_ids)
        return {
            "format": "SPLUNK_DASHBOARD_STUDIO_JSON",
            "schema_reference": self.registry.design_reference.reference,
            "dashboard_id": pack.dashboard_id,
            "scenario_id": pack.scenario_id,
            "run_id": pack.run_id,
            "definition": definition,
            "validation": validation,
            "deployment": self.deployment_preview(pack, validation),
        }

    @staticmethod
    def validate_export(
        definition: Dict[str, Any], expected_visualizations: List[str]
    ) -> Dict[str, Any]:
        required_sections = {
            "title",
            "description",
            "inputs",
            "defaults",
            "visualizations",
            "dataSources",
            "layout",
            "expressions",
            "applicationProperties",
        }
        failures = []
        missing = sorted(required_sections - set(definition))
        if missing:
            failures.append("missing sections: {}".format(", ".join(missing)))
        visualizations = set(definition.get("visualizations", {}))
        if visualizations != set(expected_visualizations):
            failures.append("layout visualization IDs do not match")
        structure_ids = {
            item["item"]
            for layout in definition.get("layout", {})
            .get("layoutDefinitions", {})
            .values()
            for item in layout.get("structure", [])
        }
        if structure_ids != visualizations:
            failures.append("layout does not reference every visualization")
        for source_id, source in definition.get("dataSources", {}).items():
            query = source.get("options", {}).get("query", "")
            if "earliest=" not in query or "latest=" not in query:
                failures.append("{} search is not time bounded".format(source_id))
            if "| join" in query.lower():
                failures.append("{} uses a forbidden join".format(source_id))
        return {
            "valid": not failures,
            "failures": failures,
            "validated_sections": sorted(required_sections - set(missing)),
        }

    @staticmethod
    def deployment_preview(
        pack: DashboardPack, export_validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "target": "AUTHORIZED_LAB_ONLY",
            "dashboard_name": pack.title,
            "dashboard_identifier": pack.dashboard_id,
            "required_permissions": ["edit_dashboard", "search"],
            "search_workload": {
                "search_count": sum(item.executable for item in pack.panels),
                "time_bound": "-15m to now",
                "joins": 0,
            },
            "validation_status": (
                "EXPORT_VALIDATED"
                if export_validation.get("valid")
                else "BLOCKED"
            ),
            "deployment_status": "PREVIEW_ONLY",
            "overwrite_allowed": False,
            "reason": (
                "No deployment occurs without an explicit authorized lab "
                "destination and non-overwrite approval."
            ),
        }
