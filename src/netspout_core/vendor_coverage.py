"""Vendor-neutral product coverage and evidence projection.

Coverage records reference the authoritative telemetry and Pack registries.
They never provide executable implementation references themselves.
"""

from enum import Enum
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from pydantic import Field, model_validator

from netspout_core.catalog_contracts import StrictModel, VerificationState
from netspout_core.pack_contracts import IntegrationRequirement, PackRegistry, SplPortability


class CoverageMaturity(str, Enum):
    DISCOVERED = "DISCOVERED"
    RESEARCHED = "RESEARCHED"
    CONTRACTED = "CONTRACTED"
    FORMAT_VALIDATED = "FORMAT_VALIDATED"
    RUNTIME_VALIDATED = "RUNTIME_VALIDATED"
    SPLUNK_VALIDATED = "SPLUNK_VALIDATED"
    GOLDEN = "GOLDEN"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


class AliasRelationship(str, Enum):
    CURRENT_NAME = "CURRENT_NAME"
    FORMER_NAME = "FORMER_NAME"
    RELATED_PRODUCT = "RELATED_PRODUCT"
    SUCCESSOR = "SUCCESSOR"


class EvidenceConfidence(str, Enum):
    AUTHORITATIVE = "AUTHORITATIVE"
    CORROBORATED = "CORROBORATED"
    LIMITED = "LIMITED"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"


class EvidenceClaim(StrictModel):
    claim_id: str
    claim: str
    evidence_type: str
    source_title: str
    publisher: str
    reference: str
    product_applicability: List[str] = Field(default_factory=list)
    software_version_applicability: List[str] = Field(default_factory=list)
    verified_date: str
    confidence: EvidenceConfidence
    status: VerificationState
    notes: str = ""
    license_or_terms: str = "REFERENCE_ONLY"
    repository_storage: str = "REFERENCE_ONLY"


class ProductAlias(StrictModel):
    name: str
    relationship: AliasRelationship
    evidence_ids: List[str]


class SplunkRelationship(StrictModel):
    requirement: IntegrationRequirement
    integration_ids: List[str] = Field(default_factory=list)
    sourcetypes: List[str] = Field(default_factory=list)
    cim_status: str = "CIM_NOT_VALIDATED"
    evidence_ids: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_guessed_integrations(self):
        if self.requirement in {
            IntegrationRequirement.REQUIRED,
            IntegrationRequirement.RECOMMENDED,
        } and not self.integration_ids:
            raise ValueError("required/recommended Splunk relationships need an integration")
        if self.integration_ids and not self.evidence_ids:
            raise ValueError("Splunk relationships require evidence")
        return self


class ProductSourceCoverage(StrictModel):
    coverage_id: str
    source_id: Optional[str] = None
    name: str
    native_format: Optional[str] = None
    transport_ids: List[str] = Field(default_factory=list)
    schema_references: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    netspout_contract_id: Optional[str] = None
    generator_status: str
    maturity: CoverageMaturity
    splunk: SplunkRelationship
    limitations: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fail_closed(self):
        if self.maturity in {
            CoverageMaturity.RESEARCH_REQUIRED,
            CoverageMaturity.UNSUPPORTED,
        } and self.generator_status in {"AVAILABLE", "READY"}:
            raise ValueError("unverified source coverage cannot be generator-ready")
        return self


class ProductCoverage(StrictModel):
    product_id: str
    vendor_id: str
    family_id: str
    current_name: str
    aliases: List[ProductAlias] = Field(default_factory=list)
    lifecycle_status: str = "UNKNOWN"
    version_applicability: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    pack_id: Optional[str] = None
    sources: List[ProductSourceCoverage] = Field(default_factory=list)
    investigation_ids: List[str] = Field(default_factory=list)
    scenario_ids: List[str] = Field(default_factory=list)
    maturity: CoverageMaturity
    limitations: List[str] = Field(default_factory=list)
    research_gaps: List[str] = Field(default_factory=list)


class CoverageFamily(StrictModel):
    family_id: str
    name: str
    product_ids: List[str]


class TroubleshootingOperation(StrictModel):
    operation_id: str
    product_ids: List[str]
    operation_type: str
    operation: str
    purpose: str
    expected_result_model: str
    platform_applicability: List[str]
    software_version_applicability: List[str]
    evidence_ids: List[str]


class ProductionReplicationGuide(StrictModel):
    guide_id: str
    scenario_id: str
    real_sources: List[str]
    collection_mechanisms: List[str]
    integration_requirements: List[str]
    sourcetypes: List[str]
    cim_requirements: List[str]
    production_portable_spl: List[str]
    prerequisites: List[str]
    netspout_differences: List[str]
    known_gaps: List[str]
    unvalidated_assumptions: List[str]


class GoldenScenarioCoverage(StrictModel):
    scenario_id: str
    title: str
    description: str
    product_ids: List[str]
    source_ids: List[str]
    shared_state: bool
    native_runtime: bool
    studio_pack: bool
    investigation_ids: List[str]
    troubleshooting_operation_ids: List[str]
    production_guide_id: str
    spl_portability: Dict[str, SplPortability]
    maturity: CoverageMaturity


class VendorCoverageCatalog(StrictModel):
    schema_version: str
    catalog_version: str
    vendor_id: str
    vendor_name: str
    independence_notice: str
    evidence: List[EvidenceClaim]
    families: List[CoverageFamily]
    products: List[ProductCoverage]
    troubleshooting: List[TroubleshootingOperation] = Field(default_factory=list)
    production_guides: List[ProductionReplicationGuide] = Field(default_factory=list)
    golden_scenarios: List[GoldenScenarioCoverage] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_relationships(self):
        evidence_ids = _unique(self.evidence, "claim_id", "evidence")
        family_ids = _unique(self.families, "family_id", "family")
        product_ids = _unique(self.products, "product_id", "product")
        troubleshooting_ids = _unique(
            self.troubleshooting, "operation_id", "troubleshooting operation"
        )
        guide_ids = _unique(self.production_guides, "guide_id", "production guide")
        scenario_ids = _unique(self.golden_scenarios, "scenario_id", "golden scenario")

        for family in self.families:
            _refs(family.product_ids, product_ids, family.family_id, "product")
        for product in self.products:
            _refs([product.family_id], family_ids, product.product_id, "family")
            _refs(product.evidence_ids, evidence_ids, product.product_id, "evidence")
            for alias in product.aliases:
                _refs(alias.evidence_ids, evidence_ids, product.product_id, "alias evidence")
            for source in product.sources:
                _refs(source.evidence_ids, evidence_ids, source.coverage_id, "evidence")
                _refs(
                    source.splunk.evidence_ids,
                    evidence_ids,
                    source.coverage_id,
                    "Splunk evidence",
                )
        for operation in self.troubleshooting:
            _refs(operation.product_ids, product_ids, operation.operation_id, "product")
            _refs(operation.evidence_ids, evidence_ids, operation.operation_id, "evidence")
        for scenario in self.golden_scenarios:
            _refs(scenario.product_ids, product_ids, scenario.scenario_id, "product")
            _refs(
                scenario.troubleshooting_operation_ids,
                troubleshooting_ids,
                scenario.scenario_id,
                "troubleshooting operation",
            )
            _refs(
                [scenario.production_guide_id],
                guide_ids,
                scenario.scenario_id,
                "production guide",
            )
        for guide in self.production_guides:
            _refs([guide.scenario_id], scenario_ids, guide.guide_id, "golden scenario")
        return self

    def validate_against(
        self,
        *,
        source_ids: Set[str],
        integration_ids: Set[str],
        registry: PackRegistry,
    ) -> None:
        pack_ids = {item.pack_id for item in registry.packs}
        scenario_ids = {
            item.scenario_id for pack in registry.packs for item in pack.scenarios
        }
        investigation_ids = {
            item.recipe_id for pack in registry.packs for item in pack.investigations
        }
        for product in self.products:
            if product.pack_id:
                _refs([product.pack_id], pack_ids, product.product_id, "pack")
            _refs(product.scenario_ids, scenario_ids, product.product_id, "scenario")
            _refs(
                product.investigation_ids,
                investigation_ids,
                product.product_id,
                "investigation",
            )
            for source in product.sources:
                if source.source_id:
                    _refs([source.source_id], source_ids, source.coverage_id, "source")
                _refs(
                    source.splunk.integration_ids,
                    integration_ids,
                    source.coverage_id,
                    "integration",
                )
        for scenario in self.golden_scenarios:
            _refs([scenario.scenario_id], scenario_ids, scenario.scenario_id, "scenario")
            _refs(scenario.source_ids, source_ids, scenario.scenario_id, "source")
            _refs(
                scenario.investigation_ids,
                investigation_ids,
                scenario.scenario_id,
                "investigation",
            )

    def summary(self) -> Dict[str, object]:
        sources = [source for product in self.products for source in product.sources]
        return {
            "vendor_id": self.vendor_id,
            "products_researched": sum(
                product.maturity != CoverageMaturity.DISCOVERED
                for product in self.products
            ),
            "source_contracts": sum(bool(source.source_id) for source in sources),
            "golden_sources": sum(
                source.maturity == CoverageMaturity.GOLDEN for source in sources
            ),
            "golden_scenarios": sum(
                scenario.maturity == CoverageMaturity.GOLDEN
                for scenario in self.golden_scenarios
            ),
            "research_required": sum(
                source.maturity == CoverageMaturity.RESEARCH_REQUIRED
                for source in sources
            ),
        }


class VendorCoverageService:
    def __init__(
        self,
        registry: PackRegistry,
        source_ids: Set[str],
        integration_ids: Set[str],
        path: Optional[Path] = None,
    ):
        root = Path(__file__).resolve().parents[2]
        configured = os.environ.get("NETSPOUT_COVERAGE_CATALOG")
        catalog_path = path or Path(configured) if configured else path
        if catalog_path is None:
            packaged_path = Path(__file__).resolve().parent / "catalog_data" / "vendor_coverage.json"
            catalog_path = (
                packaged_path
                if packaged_path.is_file()
                else root / "catalog" / "vendor_coverage.json"
            )
        with Path(catalog_path).open("r", encoding="utf-8") as handle:
            self.catalog = VendorCoverageCatalog.model_validate(json.load(handle))
        self.catalog.validate_against(
            source_ids=source_ids,
            integration_ids=integration_ids,
            registry=registry,
        )

    def view(self) -> Dict[str, object]:
        return {
            **self.catalog.model_dump(mode="json"),
            "summary": self.catalog.summary(),
        }

    def product(self, product_id: str) -> Optional[Dict[str, object]]:
        product = next(
            (item for item in self.catalog.products if item.product_id == product_id),
            None,
        )
        if product is None:
            return None
        evidence = {
            item.claim_id: item
            for item in self.catalog.evidence
            if item.claim_id in product.evidence_ids
            or any(item.claim_id in source.evidence_ids for source in product.sources)
        }
        return {
            "product": product.model_dump(mode="json"),
            "evidence": [
                item.model_dump(mode="json") for item in evidence.values()
            ],
            "troubleshooting": [
                item.model_dump(mode="json")
                for item in self.catalog.troubleshooting
                if product_id in item.product_ids
            ],
            "golden_scenarios": [
                item.model_dump(mode="json")
                for item in self.catalog.golden_scenarios
                if product_id in item.product_ids
            ],
        }


def _unique(items, field: str, label: str) -> Set[str]:
    values: Set[str] = set()
    for item in items:
        value = getattr(item, field)
        if value in values:
            raise ValueError(f"duplicate {label}: {value}")
        values.add(value)
    return values


def _refs(values, valid: Set[str], owner: str, label: str) -> None:
    missing = sorted(set(values) - valid)
    if missing:
        raise ValueError(f"{owner} references unknown {label}: {', '.join(missing)}")
