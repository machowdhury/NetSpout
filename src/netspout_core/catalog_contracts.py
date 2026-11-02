"""Strict contracts and guardrails for the authoritative telemetry catalog."""

from datetime import date
from enum import Enum
from typing import Dict, List, Literal, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class VerificationState(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


class ProvenanceClassification(str, Enum):
    VENDOR_DOCUMENTED = "VENDOR_DOCUMENTED"
    STANDARD_DOCUMENTED = "STANDARD_DOCUMENTED"
    VERIFIED_PUBLIC_SAMPLE = "VERIFIED_PUBLIC_SAMPLE"
    SPLUNK_DOCUMENTED = "SPLUNK_DOCUMENTED"
    DATASET_VERIFIED = "DATASET_VERIFIED"
    NETSPOUT_SCHEMA = "NETSPOUT_SCHEMA"
    MODELED_PAYLOAD = "MODELED_PAYLOAD"
    MODELED_VALUE = "MODELED_VALUE"
    INFERRED = "INFERRED"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"
    UNSUPPORTED_TELEMETRY = "UNSUPPORTED_TELEMETRY"


class SourcetypeAuthority(str, Enum):
    SPLUNK_DOCUMENTED = "SPLUNK_DOCUMENTED"
    NETSPOUT_DEFINED = "NETSPOUT_DEFINED"


class EvidenceReference(StrictModel):
    evidence_id: str
    title: str
    publisher: str
    reference: str
    provenance: ProvenanceClassification
    verification_state: VerificationState
    notes: str = ""


class TransportDefinition(StrictModel):
    protocol: str
    default_port: Optional[int] = Field(default=None, ge=1, le=65535)
    encoding: Optional[str] = None


class NativeContract(StrictModel):
    contract_id: str
    verification_state: VerificationState
    format: str
    native_schema: Optional[str] = Field(
        default=None, alias="schema", serialization_alias="schema"
    )
    transports: List[TransportDefinition] = Field(default_factory=list)
    structural_fields: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class SourcetypeClaim(StrictModel):
    name: str
    authority: SourcetypeAuthority
    evidence_ids: List[str] = Field(default_factory=list)


class CimMapping(StrictModel):
    name: str
    verification_state: VerificationState
    evidence_ids: List[str] = Field(default_factory=list)


class SplunkContract(StrictModel):
    contract_id: str
    verification_state: VerificationState
    input_mechanisms: List[str] = Field(default_factory=list)
    integration_ids: List[str] = Field(default_factory=list)
    sourcetypes: List[SourcetypeClaim] = Field(default_factory=list)
    cim_mappings: List[CimMapping] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class NetSpoutContract(StrictModel):
    contract_id: str
    verification_state: VerificationState
    schema_classification: ProvenanceClassification
    generator: Optional[str] = None
    validator: Optional[str] = None
    transports: List[str] = Field(default_factory=list)
    modeled_fields: List[str] = Field(default_factory=list)
    structural_fields: List[str] = Field(default_factory=list)
    scenario_ids: List[str] = Field(default_factory=list)
    generation_modes: List[str] = Field(default_factory=list)
    runtime_status: str
    maturity: str
    evidence_ids: List[str] = Field(default_factory=list)


class SplFieldScope(StrictModel):
    production_fields: List[str] = Field(default_factory=list)
    netspout_only_fields: List[str] = Field(default_factory=list)
    portable_spl_status: VerificationState


class TelemetrySource(StrictModel):
    source_id: str
    vendor: str
    product: str
    product_family: str
    domains: List[str]
    telemetry_source: str
    applicable_industries: List[str] = Field(default_factory=list)
    verification_state: VerificationState
    provenance: List[ProvenanceClassification]
    evidence_ids: List[str] = Field(default_factory=list)
    native_contract: NativeContract
    splunk_contract: SplunkContract
    netspout_contract: NetSpoutContract
    spl_field_scope: SplFieldScope
    known_limitations: List[str] = Field(default_factory=list)


class CoverageState(str, Enum):
    NOT_ASSESSED = "not_assessed"
    MISSING = "missing"
    PARTIAL = "partial"
    SAMPLE_READY = "sample_ready"
    SCENARIO_READY = "scenario_ready"
    INTEGRATION_VERIFIED = "integration_verified"


class ProfileField(StrictModel):
    name: str = Field(min_length=1)
    data_type: Literal["string", "integer", "number", "boolean", "object", "array"]
    required: bool = True
    evidence_ids: List[str] = Field(min_length=1)


class ProfileRequirement(StrictModel):
    """Documented input/search dependencies; presence does not assert compatibility."""
    kind: Literal["source", "timestamp", "cim_dataset", "eventtype", "tag",
                  "dashboard", "search", "signal"]
    value: str = Field(min_length=1)
    details: Optional[str] = None
    evidence_ids: List[str] = Field(min_length=1)


class ProfileValidation(StrictModel):
    kind: Literal["sample_schema", "generator", "parser", "field_extraction", "cim", "dashboard"]
    outcome: Literal["passed", "failed", "inconclusive"]
    app_version: Optional[str] = None
    platform: Optional[Literal["splunk_enterprise", "splunk_cloud"]] = None
    evidence_ids: List[str] = Field(min_length=1)


class IntegrationProfile(StrictModel):
    """Version/method-specific schema assertions within the existing integration registry.

    Evidence is reviewed repository metadata, not a cryptographic attestation.
    Empty lists and null mean unknown, never an undocumented compatibility claim.
    """
    profile_id: str = Field(min_length=1)
    vendor: str = Field(min_length=1)
    product: str = Field(min_length=1)
    vendor_id: Optional[str] = None
    legacy_catalog_default: bool = False
    splunkbase_id: Optional[str] = Field(default=None, pattern=r"^[0-9]+$")
    splunkbase_url: Optional[str] = None
    publisher: Optional[str] = None
    integration_type: Literal["app", "add_on", "native_input", "collector", "custom_schema"]
    app_version: Optional[str] = Field(default=None, min_length=1)
    documentation_version: Optional[str] = None
    documentation_date: Optional[date] = None
    platforms: List[Literal["splunk_enterprise", "splunk_cloud"]] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    collection_method: Optional[str] = None
    wire_format: Optional[str] = None
    sourcetypes: List[SourcetypeClaim] = Field(default_factory=list)
    fields: List[ProfileField] = Field(default_factory=list)
    requirements: List[ProfileRequirement] = Field(default_factory=list)
    schema_known: bool = False
    coverage: CoverageState = CoverageState.NOT_ASSESSED
    verification_state: VerificationState = VerificationState.RESEARCH_REQUIRED
    evidence_ids: List[str] = Field(default_factory=list)
    validations: List[ProfileValidation] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def validate_profile(self):
        if self.splunkbase_id is not None:
            expected = "https://splunkbase.splunk.com/app/" + self.splunkbase_id
            if self.splunkbase_url != expected:
                raise ValueError("profile app ID and URL must agree")
        elif self.splunkbase_url is not None:
            raise ValueError("profile URL requires app ID")
        if self.legacy_catalog_default and not (self.vendor_id and self.splunkbase_id):
            raise ValueError("legacy projection requires stable vendor ID and app ID")
        if (self.fields or self.requirements or self.sourcetypes or self.splunkbase_id) and not self.evidence_ids:
            raise ValueError("profile claims require evidence")
        ready = {CoverageState.SAMPLE_READY, CoverageState.SCENARIO_READY,
                 CoverageState.INTEGRATION_VERIFIED}
        passed = {v.kind for v in self.validations if v.outcome == "passed"}
        if self.coverage in ready:
            if (not self.schema_known or not self.collection_method or not self.wire_format
                    or "sample_schema" not in passed
                    or self.verification_state in {VerificationState.RESEARCH_REQUIRED,
                                                   VerificationState.UNSUPPORTED}):
                raise ValueError("ready coverage requires established schema and sample validation")
        if self.coverage == CoverageState.SCENARIO_READY and "generator" not in passed:
            raise ValueError("scenario readiness requires generator validation")
        if self.coverage == CoverageState.INTEGRATION_VERIFIED:
            if not self.app_version or self.verification_state != VerificationState.VERIFIED:
                raise ValueError("integration verification requires selected app version")
            for kind in ("parser", "field_extraction"):
                if not any(v.kind == kind and v.outcome == "passed"
                           and v.app_version == self.app_version and v.platform in self.platforms
                           for v in self.validations):
                    raise ValueError("integration verification requires version/platform-bound parser and field evidence")
        return self


class SplunkIntegration(StrictModel):
    integration_id: str
    profiles: List[IntegrationProfile] = Field(default_factory=list)
    name: str
    publisher: str
    integration_type: str
    supported_source_ids: List[str] = Field(default_factory=list)
    splunkbase_id: Optional[str] = None
    verification_state: VerificationState
    support_state: str
    sourcetypes: List[SourcetypeClaim] = Field(default_factory=list)
    cim_mappings: List[CimMapping] = Field(default_factory=list)
    netspout_coverage: VerificationState
    evidence_ids: List[str] = Field(default_factory=list)
    notes: str = ""


class SourceManifest(StrictModel):
    manifest_id: str
    scenario_id: str
    verification_state: VerificationState
    source_ids: List[str]
    notes: str = ""


class TelemetryCatalog(StrictModel):
    schema_version: str
    catalog_version: str
    evidence: List[EvidenceReference]
    integrations: List[SplunkIntegration]
    sources: List[TelemetrySource]
    source_manifests: List[SourceManifest]

    @model_validator(mode="after")
    def validate_relationships(self):
        evidence_ids = _unique_ids(self.evidence, "evidence_id", "evidence")
        integration_ids = _unique_ids(self.integrations, "integration_id", "integration")
        source_ids = _unique_ids(self.sources, "source_id", "source")
        _unique_ids(self.source_manifests, "manifest_id", "source manifest")

        identities: Set[str] = set()
        for source in self.sources:
            identity = "|".join(
                part.strip().lower()
                for part in (source.vendor, source.product, source.telemetry_source)
            )
            if identity in identities:
                raise ValueError("duplicate source identity: {}".format(identity))
            identities.add(identity)

            _require_references(source.evidence_ids, evidence_ids, source.source_id, "evidence")
            _require_references(
                source.native_contract.evidence_ids, evidence_ids, source.source_id, "native evidence"
            )
            _require_references(
                source.splunk_contract.evidence_ids, evidence_ids, source.source_id, "Splunk evidence"
            )
            _require_references(
                source.netspout_contract.evidence_ids,
                evidence_ids,
                source.source_id,
                "NetSpout evidence",
            )
            _require_references(
                source.splunk_contract.integration_ids,
                integration_ids,
                source.source_id,
                "integration",
            )

            if source.verification_state == VerificationState.UNSUPPORTED:
                if (
                    source.netspout_contract.verification_state
                    != VerificationState.UNSUPPORTED
                    or source.netspout_contract.runtime_status != "UNSUPPORTED"
                ):
                    raise ValueError(
                        "unsupported source '{}' must fail closed".format(source.source_id)
                    )
            if source.verification_state == VerificationState.RESEARCH_REQUIRED:
                if source.netspout_contract.runtime_status in {"READY", "AVAILABLE"}:
                    raise ValueError(
                        "research-required source '{}' cannot be runtime ready".format(
                            source.source_id
                        )
                    )

            for claim in source.splunk_contract.sourcetypes:
                self._validate_sourcetype_claim(claim, evidence_ids, source.source_id)

        profile_ids: Set[str] = set()
        default_vendors: Set[str] = set()
        evidence_by_id = {item.evidence_id: item for item in self.evidence}
        for integration in self.integrations:
            for profile in integration.profiles:
                if profile.profile_id in profile_ids:
                    raise ValueError("duplicate integration profile ID")
                profile_ids.add(profile.profile_id)
                if profile.splunkbase_id != integration.splunkbase_id:
                    raise ValueError("profile and integration app identities must agree")
                if profile.legacy_catalog_default:
                    if profile.vendor_id in default_vendors:
                        raise ValueError("multiple legacy defaults for one vendor")
                    default_vendors.add(profile.vendor_id)
                _require_references(profile.evidence_ids, evidence_ids, profile.profile_id, "profile evidence")
                for claim in profile.sourcetypes:
                    self._validate_sourcetype_claim(claim, evidence_ids, profile.profile_id)
                for assertion in [*profile.fields, *profile.requirements, *profile.validations]:
                    _require_references(assertion.evidence_ids, evidence_ids, profile.profile_id, "profile evidence")
                for assertion in [*profile.fields, *profile.requirements]:
                    if not any(evidence_by_id[e].verification_state in {
                            VerificationState.VERIFIED, VerificationState.PARTIALLY_VERIFIED}
                            and evidence_by_id[e].provenance in {
                                ProvenanceClassification.VENDOR_DOCUMENTED,
                                ProvenanceClassification.SPLUNK_DOCUMENTED,
                                ProvenanceClassification.STANDARD_DOCUMENTED,
                                ProvenanceClassification.NETSPOUT_SCHEMA,
                                ProvenanceClassification.DATASET_VERIFIED}
                            for e in assertion.evidence_ids):
                        raise ValueError("schema requirements need established evidence, not inferred mappings")
                for validation in profile.validations:
                    if validation.outcome == "passed" and validation.kind in {"parser", "field_extraction", "cim", "dashboard"}:
                        if (not profile.app_version or validation.app_version != profile.app_version
                                or validation.platform not in profile.platforms
                                or not any(evidence_by_id[e].provenance == ProvenanceClassification.DATASET_VERIFIED
                                           and evidence_by_id[e].verification_state == VerificationState.VERIFIED
                                           for e in validation.evidence_ids)):
                            raise ValueError("integration validation requires version-bound verified dataset evidence")
            _require_references(
                integration.supported_source_ids,
                source_ids,
                integration.integration_id,
                "source",
            )
            _require_references(
                integration.evidence_ids,
                evidence_ids,
                integration.integration_id,
                "evidence",
            )
            for claim in integration.sourcetypes:
                self._validate_sourcetype_claim(
                    claim, evidence_ids, integration.integration_id
                )

        for source in self.sources:
            for integration_id in source.splunk_contract.integration_ids:
                integration = next(
                    item for item in self.integrations if item.integration_id == integration_id
                )
                if source.source_id not in integration.supported_source_ids:
                    raise ValueError(
                        "source '{}' and integration '{}' relationship is not symmetric".format(
                            source.source_id, integration_id
                        )
                    )

        for manifest in self.source_manifests:
            _require_references(
                manifest.source_ids, source_ids, manifest.manifest_id, "source"
            )
        return self

    def _validate_sourcetype_claim(
        self, claim: SourcetypeClaim, evidence_ids: Set[str], owner: str
    ) -> None:
        _require_references(claim.evidence_ids, evidence_ids, owner, "sourcetype evidence")
        evidence_by_id: Dict[str, EvidenceReference] = {
            item.evidence_id: item for item in self.evidence
        }
        classifications = {
            evidence_by_id[evidence_id].provenance for evidence_id in claim.evidence_ids
        }
        if claim.authority == SourcetypeAuthority.SPLUNK_DOCUMENTED:
            if ProvenanceClassification.SPLUNK_DOCUMENTED not in classifications:
                raise ValueError(
                    "official sourcetype claim '{}' lacks Splunk evidence".format(claim.name)
                )
        elif ProvenanceClassification.NETSPOUT_SCHEMA not in classifications:
            raise ValueError(
                "NetSpout-defined sourcetype '{}' lacks NetSpout schema evidence".format(
                    claim.name
                )
            )


def _unique_ids(items, field: str, label: str) -> Set[str]:
    result: Set[str] = set()
    for item in items:
        value = getattr(item, field)
        if value in result:
            raise ValueError("duplicate {} id: {}".format(label, value))
        result.add(value)
    return result


def _require_references(
    references: List[str], valid_ids: Set[str], owner: str, label: str
) -> None:
    missing = sorted(set(references) - valid_ids)
    if missing:
        raise ValueError(
            "{} '{}' references unknown values: {}".format(label, owner, ", ".join(missing))
        )


LEGACY_PROVENANCE_MAP = {
    "VENDOR_DOCUMENTED": ProvenanceClassification.VENDOR_DOCUMENTED.value,
    "STANDARDS_BASED": ProvenanceClassification.STANDARD_DOCUMENTED.value,
    "SPLUNK_AUTHORITATIVE": ProvenanceClassification.SPLUNK_DOCUMENTED.value,
    "VENDOR VERIFIED": ProvenanceClassification.VENDOR_DOCUMENTED.value,
    "STANDARD VERIFIED": ProvenanceClassification.STANDARD_DOCUMENTED.value,
    "SPLUNK VERIFIED": ProvenanceClassification.SPLUNK_DOCUMENTED.value,
    "DATASET VERIFIED": ProvenanceClassification.DATASET_VERIFIED.value,
    "NETSPOUT SCHEMA": ProvenanceClassification.NETSPOUT_SCHEMA.value,
    "MODELED PAYLOAD": ProvenanceClassification.MODELED_PAYLOAD.value,
    "MODELED VALUE": ProvenanceClassification.MODELED_VALUE.value,
    "RESEARCH REQUIRED": ProvenanceClassification.RESEARCH_REQUIRED.value,
    "UNSUPPORTED": ProvenanceClassification.UNSUPPORTED_TELEMETRY.value,
}


def project_integration_identities(vendors: list, catalog: TelemetryCatalog) -> list:
    """Project explicit profile defaults without changing stable vendor identities.

    Used by both full and profile-only canonical generation; never guesses a default
    from profile ordering. Returns independent records so rejection is non-mutating.
    """
    from copy import deepcopy
    result = deepcopy(vendors)
    by_id = {vendor["id"]: vendor for vendor in result}
    for integration in catalog.integrations:
        for profile in integration.profiles:
            if not profile.legacy_catalog_default:
                continue
            if profile.vendor_id not in by_id:
                raise ValueError("profile references unknown stable vendor ID")
            by_id[profile.vendor_id].update(
                splunk_app_name=integration.name,
                splunkbase_id=profile.splunkbase_id,
                splunkbase_url=profile.splunkbase_url,
            )
    return result
