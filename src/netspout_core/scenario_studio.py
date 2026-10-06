"""Safe, local Scenario Studio and Custom Source Pack primitives.

The Studio deliberately separates authored modeled state from immutable
telemetry contracts. Imported samples are scanned locally and are never
persisted until a caller supplies a reviewed, sanitized sample.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import sys
import tempfile
import threading
from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pydantic import Field, model_validator

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.catalog_contracts import (
    EvidenceReference,
    NativeContract,
    NetSpoutContract,
    ProvenanceClassification,
    SourcetypeAuthority,
    SourcetypeClaim,
    SplFieldScope,
    SplunkContract,
    TelemetrySource,
    TransportDefinition,
    VerificationState,
)
from netspout_core.pack_contracts import (
    CompositionDefinition,
    DestinationDefinition,
    GeneratorDefinition,
    GuidedInvestigationStep,
    GuidedScenarioManifest,
    IncidentEvidence,
    InvestigationRecipe,
    PackDefinition,
    PackKind,
    PackMaturity,
    RawFidelityPolicy,
    ReplayPolicy,
    ScenarioParameter,
    ScenarioStage,
    ScenarioValidationExpectation,
    ScenarioVisualization,
    SourceBinding,
    SourcePackEntry,
    SplPortability,
    StrictModel,
    TelemetryPath,
    TelemetrySignal,
    TimelineStep,
    TopologyNode,
    TopologyRelationship,
    TopologyZone,
    TransportCapability,
    ValidationRequirement,
    ValidationStage,
    ValidatorDefinition,
    VisualizationMode,
    CustomSourceLifecycle,
    PromotionAuthority,
)


class CreationPath(str, Enum):
    EXISTING_SOURCES = "EXISTING_SOURCES"
    IMPORT_SANITIZED_SAMPLE = "IMPORT_SANITIZED_SAMPLE"
    CLONE_SCENARIO = "CLONE_SCENARIO"


class FieldClassification(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    MODELED = "MODELED"
    CORRELATION = "CORRELATION"
    DERIVED = "DERIVED"
    SENSITIVE = "SENSITIVE"
    UNKNOWN = "UNKNOWN"


class ClassificationAuthority(str, Enum):
    INFERRED = "INFERRED"
    USER_PROVIDED = "USER_PROVIDED"
    CATALOG_VERIFIED = "CATALOG_VERIFIED"


class PrivacyStatus(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    FINDINGS_REQUIRE_REVIEW = "FINDINGS_REQUIRE_REVIEW"
    SANITIZED = "SANITIZED"


class SampleProvenance(str, Enum):
    CUSTOMER_SAMPLE_SANITIZED = "CUSTOMER SAMPLE — SANITIZED"
    LAB_SAMPLE_SANITIZED = "LAB SAMPLE — SANITIZED"
    PUBLIC_SAMPLE = "PUBLIC SAMPLE"
    VENDOR_DOCUMENTED = "VENDOR DOCUMENTED"
    UNKNOWN_ORIGIN = "UNKNOWN ORIGIN"
    NETSPOUT_GENERATED = "NETSPOUT GENERATED"


class RedistributionStatus(str, Enum):
    PRIVATE = "PRIVATE"
    LOCAL_ONLY = "LOCAL ONLY"
    REDISTRIBUTION_UNKNOWN = "REDISTRIBUTION UNKNOWN"
    REDISTRIBUTION_PERMITTED = "REDISTRIBUTION PERMITTED"


class StudioMaturity(str, Enum):
    DRAFT = "DRAFT"
    STRUCTURE_VALIDATED = "STRUCTURE VALIDATED"
    SOURCE_VALIDATED = "SOURCE VALIDATED"
    RUNTIME_VALIDATED = "RUNTIME VALIDATED"
    SPLUNK_VALIDATED = "SPLUNK VALIDATED"
    READY = "READY"


class FindingCategory(str, Enum):
    CREDENTIAL = "CREDENTIAL"
    PRIVATE_KEY = "PRIVATE_KEY"
    CERTIFICATE = "CERTIFICATE"
    EMAIL = "EMAIL"
    IP_ADDRESS = "IP_ADDRESS"
    MAC_ADDRESS = "MAC_ADDRESS"
    HOSTNAME_OR_DOMAIN = "HOSTNAME_OR_DOMAIN"
    UUID = "UUID"
    USERNAME = "USERNAME"
    SERIAL_NUMBER = "SERIAL_NUMBER"
    TENANT_OR_ACCOUNT_ID = "TENANT_OR_ACCOUNT_ID"
    CUSTOMER_IDENTIFIER = "CUSTOMER_IDENTIFIER"


class PrivacyFinding(StrictModel):
    category: FindingCategory
    location: str
    redacted_preview: str
    severity: str
    fingerprint: str


class SampleField(StrictModel):
    name: str
    data_type: str
    classification: FieldClassification
    authority: ClassificationAuthority = ClassificationAuthority.INFERRED
    description: str = ""
    enum_values: List[str] = Field(default_factory=list)
    numeric_min: Optional[float] = None
    numeric_max: Optional[float] = None


class SampleAnalysisRequest(StrictModel):
    sample: str = Field(min_length=1, max_length=200_000)
    authorization_acknowledged: bool
    format_hint: Optional[str] = None

    @model_validator(mode="after")
    def require_authorization(self):
        if not self.authorization_acknowledged:
            raise ValueError(
                "Import requires acknowledgement that the sample is authorized "
                "and has been reviewed for sensitive data."
            )
        return self


class SampleAnalysisResult(StrictModel):
    sample_fingerprint: str
    blocked: bool
    privacy_status: PrivacyStatus
    findings: List[PrivacyFinding]
    format: str
    record_count: int
    fields: List[SampleField]
    record_boundary: str
    notes: List[str] = Field(default_factory=list)


class CustomSourceDraft(StrictModel):
    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    display_name: str = Field(min_length=3, max_length=120)
    sanitized_sample: str = Field(min_length=1, max_length=200_000)
    analyzed_fingerprint: str
    privacy_status: PrivacyStatus
    provenance: SampleProvenance
    redistribution: RedistributionStatus = RedistributionStatus.PRIVATE
    fields: List[SampleField]
    format: str
    source_description: str
    netspout_sourcetype: Optional[str] = None
    netspout_sourcetype_acknowledged: bool = False

    @model_validator(mode="after")
    def enforce_private_reviewed_source(self):
        if self.privacy_status != PrivacyStatus.SANITIZED:
            raise ValueError("custom sources require an approved sanitized sample")
        if self.provenance == SampleProvenance.CUSTOMER_SAMPLE_SANITIZED:
            if self.redistribution not in {
                RedistributionStatus.PRIVATE,
                RedistributionStatus.LOCAL_ONLY,
                RedistributionStatus.REDISTRIBUTION_UNKNOWN,
            }:
                raise ValueError(
                    "customer samples cannot be marked redistribution permitted "
                    "without a separate rights review"
                )
        if self.netspout_sourcetype and not self.netspout_sourcetype_acknowledged:
            raise ValueError(
                "a private custom sourcetype must be explicitly acknowledged "
                "as NETSPOUT-DEFINED"
            )
        return self


class StudioEntity(StrictModel):
    entity_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{1,79}$")
    label: str
    entity_type: str
    zone_id: str
    attributes: Dict[str, str] = Field(default_factory=dict)
    x: Optional[float] = None
    y: Optional[float] = None


class StudioRelationship(StrictModel):
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    protocol: Optional[str] = None


class StudioStateValue(StrictModel):
    state_key: str
    entity_id: str
    value: Any
    unit: Optional[str] = None


class StudioTransition(StrictModel):
    transition_id: str
    stage: ScenarioStage
    offset_seconds: int = Field(ge=0, le=86_400)
    title: str
    state_changes: List[StudioStateValue]
    source_ids: List[str] = Field(default_factory=list)


class StudioParameter(StrictModel):
    parameter_id: str
    state_key: str
    value_type: str
    default: Any
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    enum_values: List[str] = Field(default_factory=list)
    unit: Optional[str] = None
    description: str = ""

    def validate_value(self, value: Any) -> Optional[str]:
        if self.value_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return "must be a number"
            if self.minimum is not None and value < self.minimum:
                return "must be at least {}".format(self.minimum)
            if self.maximum is not None and value > self.maximum:
                return "must be at most {}".format(self.maximum)
        elif self.value_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                return "must be an integer"
        elif self.value_type == "boolean":
            if not isinstance(value, bool):
                return "must be a boolean"
        elif self.value_type == "enum":
            if value not in self.enum_values:
                return "must be one of {}".format(", ".join(self.enum_values))
        elif not isinstance(value, str):
            return "must be a string"
        return None


class CorrelationMapping(StrictModel):
    source_id: str
    source_field: str
    entity_id: str
    identity_type: str


class StudioInvestigation(StrictModel):
    investigation_id: str
    title: str
    objective: str
    question: str
    spl: str
    expected_finding: str
    explanation: str
    portability: SplPortability
    evidence_source_ids: List[str]
    netspout_only_fields: List[str] = Field(default_factory=list)


class StudioScenarioPack(StrictModel):
    pack_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    title: str = Field(min_length=3, max_length=120)
    description: str
    story: str
    creation_path: CreationPath
    maturity: StudioMaturity = StudioMaturity.DRAFT
    privacy_status: PrivacyStatus = PrivacyStatus.SANITIZED
    provenance: SampleProvenance = SampleProvenance.NETSPOUT_GENERATED
    redistribution: RedistributionStatus = RedistributionStatus.PRIVATE
    source_ids: List[str]
    custom_sources: List[CustomSourceDraft] = Field(default_factory=list)
    zones: List[TopologyZone]
    entities: List[StudioEntity]
    relationships: List[StudioRelationship]
    baseline: List[StudioStateValue]
    timeline: List[StudioTransition]
    parameters: List[StudioParameter] = Field(default_factory=list)
    correlation_mappings: List[CorrelationMapping] = Field(default_factory=list)
    investigations: List[StudioInvestigation] = Field(default_factory=list)
    contract_fingerprints: Dict[str, str] = Field(default_factory=dict)
    layout_hints: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    cloned_from_scenario_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @model_validator(mode="after")
    def preserve_private_boundary(self):
        if self.custom_sources and self.redistribution not in {
            RedistributionStatus.PRIVATE,
            RedistributionStatus.LOCAL_ONLY,
            RedistributionStatus.REDISTRIBUTION_UNKNOWN,
        }:
            raise ValueError(
                "custom sample packs require a separate redistribution review"
            )
        if self.privacy_status != PrivacyStatus.SANITIZED:
            raise ValueError("unresolved privacy findings cannot enter a scenario pack")
        return self


class StudioValidationCheck(StrictModel):
    check_id: str
    state: str
    detail: str


class StudioValidationReport(StrictModel):
    valid: bool
    maturity_ceiling: StudioMaturity
    checks: List[StudioValidationCheck]
    errors: List[str]
    warnings: List[str]


class StudioDraftRequest(StrictModel):
    creation_path: CreationPath
    source_ids: List[str] = Field(default_factory=list)
    clone_scenario_id: Optional[str] = None
    title: str = "Untitled private scenario"


class StudioRunRequest(StrictModel):
    parameters: Dict[str, Any] = Field(default_factory=dict)
    seed: int = Field(default=606, ge=0, le=2_147_483_647)


_SAFE_STATE_INPUTS: Dict[str, set] = {
    "ietf-syslog-rfc5424": {
        "interface.status",
        "interface.loss",
        "application.latency",
        "application.error_rate",
    },
    "ietf-snmpv2c-ifmib": {
        "interface.status",
        "interface.utilization",
        "interface.loss",
    },
    "openconfig-gnmi-interfaces": {
        "interface.status",
        "interface.utilization",
        "interface.loss",
    },
    "ietf-netflow-v9": {"interface.utilization", "flow.intensity"},
    "ietf-ipfix": {"interface.utilization", "flow.intensity"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _redact(value: str) -> str:
    return "[REDACTED]"


def _is_documentation_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    networks = (
        ipaddress.ip_network("192.0.2.0/24"),
        ipaddress.ip_network("198.51.100.0/24"),
        ipaddress.ip_network("203.0.113.0/24"),
        ipaddress.ip_network("2001:db8::/32"),
    )
    return any(address in network for network in networks)


class SensitiveDataScanner:
    """Conservative local scanner. Findings are redacted and never persisted."""

    _PATTERNS: Sequence[Tuple[FindingCategory, str, re.Pattern, str]] = (
        (
            FindingCategory.PRIVATE_KEY,
            "CRITICAL",
            re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
            "private-key material",
        ),
        (
            FindingCategory.CERTIFICATE,
            "HIGH",
            re.compile(r"-----BEGIN CERTIFICATE-----"),
            "certificate material",
        ),
        (
            FindingCategory.CREDENTIAL,
            "CRITICAL",
            re.compile(
                r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|"
                r"refresh[_-]?token|authorization)\b\s*[:=]\s*[\"']?([^\s,\"'}]{6,})"
            ),
            "credential-like value",
        ),
        (
            FindingCategory.CREDENTIAL,
            "CRITICAL",
            re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/=-]{8,})"),
            "bearer credential",
        ),
        (
            FindingCategory.CREDENTIAL,
            "CRITICAL",
            re.compile(
                r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA)[A-Z0-9]{12,}\b"
                r"|\b(?:gh[opusr]_[A-Za-z0-9]{20,}|"
                r"(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{12,})\b"
            ),
            "credential token",
        ),
        (
            FindingCategory.CREDENTIAL,
            "CRITICAL",
            re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]+:([^@\s/]+)@"),
            "credential-bearing URL",
        ),
        (
            FindingCategory.EMAIL,
            "HIGH",
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "email address",
        ),
        (
            FindingCategory.UUID,
            "MEDIUM",
            re.compile(
                r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
                r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
            ),
            "UUID",
        ),
        (
            FindingCategory.MAC_ADDRESS,
            "MEDIUM",
            re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"),
            "MAC address",
        ),
        (
            FindingCategory.IP_ADDRESS,
            "MEDIUM",
            re.compile(
                r"(?<![0-9A-Fa-f:.])(?:\d{1,3}\.){3}\d{1,3}"
                r"(?![0-9A-Fa-f:.])"
            ),
            "IP address",
        ),
        (
            FindingCategory.IP_ADDRESS,
            "MEDIUM",
            re.compile(
                r"(?<![0-9A-Fa-f:])[0-9A-Fa-f]*:"
                r"[0-9A-Fa-f:]+(?![0-9A-Fa-f:])"
            ),
            "IPv6 address",
        ),
        (
            FindingCategory.HOSTNAME_OR_DOMAIN,
            "MEDIUM",
            re.compile(
                r"\b(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
                r"(?:com|net|org|io|corp|local|internal|cloud|dev)\b",
                re.IGNORECASE,
            ),
            "hostname or domain",
        ),
        (
            FindingCategory.SERIAL_NUMBER,
            "MEDIUM",
            re.compile(
                r"(?i)\b(?:serial|serial_number|device_serial)\b\s*[:=]\s*"
                r"[\"']?([A-Za-z0-9-]{6,})"
            ),
            "serial number",
        ),
        (
            FindingCategory.TENANT_OR_ACCOUNT_ID,
            "HIGH",
            re.compile(
                r"(?i)\b(?:tenant[_-]?id|account[_-]?id|subscription[_-]?id)\b"
                r"\s*[:=]\s*[\"']?([A-Za-z0-9-]{6,})"
            ),
            "tenant or account identifier",
        ),
        (
            FindingCategory.USERNAME,
            "MEDIUM",
            re.compile(
                r"(?i)\b(?:user|username|user_name|principal)\b\s*[:=]\s*"
                r"[\"']?([A-Za-z][A-Za-z0-9._-]{2,})"
            ),
            "username",
        ),
        (
            FindingCategory.CUSTOMER_IDENTIFIER,
            "MEDIUM",
            re.compile(
                r"(?i)\b(?:customer[_-]?id|organization[_-]?id|org[_-]?id|"
                r"lab[_-]?id)\b\s*[:=]\s*[\"']?([A-Za-z0-9-]{4,})"
            ),
            "environment-specific identifier",
        ),
    )

    def scan(self, sample: str) -> List[PrivacyFinding]:
        findings: List[PrivacyFinding] = []
        seen = set()
        for line_number, line in enumerate(sample.splitlines() or [sample], start=1):
            for category, severity, pattern, label in self._PATTERNS:
                for match in pattern.finditer(line):
                    value = match.group(1) if match.lastindex else match.group(0)
                    normalized = value.strip("\"'")
                    lowered = normalized.lower()
                    if category == FindingCategory.IP_ADDRESS and _is_documentation_ip(
                        normalized
                    ):
                        continue
                    if category == FindingCategory.IP_ADDRESS and ":" in normalized:
                        try:
                            ipaddress.ip_address(normalized)
                        except ValueError:
                            continue
                    if category == FindingCategory.HOSTNAME_OR_DOMAIN and (
                        lowered.endswith(".example")
                        or lowered.endswith(".invalid")
                        or lowered.endswith(".test")
                    ):
                        continue
                    identity = (category.value, line_number, _fingerprint(normalized))
                    if identity in seen:
                        continue
                    seen.add(identity)
                    findings.append(
                        PrivacyFinding(
                            category=category,
                            location="line {}".format(line_number),
                            redacted_preview="{}: {}".format(label, _redact(normalized)),
                            severity=severity,
                            fingerprint=_fingerprint(
                                "{}:{}:{}".format(
                                    category.value, line_number, match.start()
                                )
                            ),
                        )
                    )
        return findings


class SampleAnalyzer:
    def __init__(self, scanner: Optional[SensitiveDataScanner] = None):
        self.scanner = scanner or SensitiveDataScanner()

    def analyze(self, request: SampleAnalysisRequest) -> SampleAnalysisResult:
        findings = self.scanner.scan(request.sample)
        records, detected_format, boundary = self._records(
            request.sample, request.format_hint
        )
        fields = self._fields(records)
        if findings:
            fields = [
                item.model_copy(update={"enum_values": []}) for item in fields
            ]
        return SampleAnalysisResult(
            sample_fingerprint=_fingerprint(request.sample),
            blocked=bool(findings),
            privacy_status=(
                PrivacyStatus.FINDINGS_REQUIRE_REVIEW
                if findings
                else PrivacyStatus.SANITIZED
            ),
            findings=findings,
            format=detected_format,
            record_count=len(records),
            fields=fields,
            record_boundary=boundary,
            notes=[
                "Analysis is local and structural only.",
                "Suggested classifications are not vendor verification.",
                "Unknown fields remain UNKNOWN until a human establishes meaning.",
            ],
        )

    @staticmethod
    def _records(
        sample: str, format_hint: Optional[str]
    ) -> Tuple[List[Dict[str, Any]], str, str]:
        hint = (format_hint or "").upper()
        if hint in {"JSON", "JSONL", ""}:
            try:
                parsed = json.loads(sample)
                if isinstance(parsed, dict):
                    return [parsed], "JSON", "single JSON object"
                if isinstance(parsed, list) and all(
                    isinstance(item, dict) for item in parsed
                ):
                    return parsed, "JSON", "JSON array items"
            except json.JSONDecodeError:
                pass
            rows = []
            for line in sample.splitlines():
                try:
                    parsed_line = json.loads(line)
                except json.JSONDecodeError:
                    rows = []
                    break
                if not isinstance(parsed_line, dict):
                    rows = []
                    break
                rows.append(parsed_line)
            if rows:
                return rows, "JSONL", "one JSON object per line"

        rows = []
        for line in [item for item in sample.splitlines() if item.strip()]:
            pairs = re.findall(
                r"([A-Za-z_][A-Za-z0-9_.-]*)=(\"[^\"]*\"|'[^']*'|[^\s]+)",
                line,
            )
            if pairs:
                rows.append(
                    {key: value.strip("\"'") for key, value in pairs}
                )
            else:
                rows.append({"raw": line})
        return rows or [{"raw": sample}], "LOGFMT" if rows else "TEXT", "newline"

    @staticmethod
    def _fields(records: List[Dict[str, Any]]) -> List[SampleField]:
        values: Dict[str, List[Any]] = {}
        for record in records:
            for key, value in record.items():
                values.setdefault(str(key), []).append(value)
        fields = []
        for name in sorted(values):
            observed = values[name]
            lowered = name.lower()
            classification = FieldClassification.UNKNOWN
            if lowered in {"timestamp", "time", "@timestamp", "duration"}:
                classification = FieldClassification.DERIVED
            elif any(
                token in lowered
                for token in ("session", "transaction", "request_id", "trace_id")
            ):
                classification = FieldClassification.CORRELATION
            elif any(
                token in lowered
                for token in (
                    "ip",
                    "host",
                    "user",
                    "device",
                    "interface",
                    "application",
                    "latency",
                    "loss",
                    "cpu",
                    "memory",
                )
            ):
                classification = FieldClassification.MODELED
            elif any(
                token in lowered
                for token in ("password", "secret", "token", "api_key")
            ):
                classification = FieldClassification.SENSITIVE
            elif len({json.dumps(item, sort_keys=True) for item in observed}) <= 4:
                classification = FieldClassification.STRUCTURAL

            type_names = sorted({type(item).__name__ for item in observed})
            numeric = [
                float(item)
                for item in observed
                if isinstance(item, (int, float)) and not isinstance(item, bool)
            ]
            enum_values = sorted(
                {
                    str(item)
                    for item in observed
                    if isinstance(item, (str, bool))
                }
            )
            fields.append(
                SampleField(
                    name=name,
                    data_type=" | ".join(type_names),
                    classification=classification,
                    enum_values=enum_values[:12],
                    numeric_min=min(numeric) if numeric else None,
                    numeric_max=max(numeric) if numeric else None,
                )
            )
        return fields


class ScenarioStudioService:
    """Owns local private packs and bridges them into existing Pack/runtime APIs."""

    def __init__(
        self,
        catalog: Optional[NetSpoutCatalog] = None,
        generation_service: Optional[Any] = None,
        storage_dir: Optional[str] = None,
    ):
        self.catalog = catalog or NetSpoutCatalog()
        self.generation_service = generation_service
        configured = storage_dir or os.environ.get("NETSPOUT_STUDIO_DIR")
        self.storage_dir = Path(
            configured or os.path.expanduser("~/.netspout/private-packs")
        ).resolve()
        self.storage_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            self.storage_dir.chmod(0o700)
        except OSError:
            pass
        self.analyzer = SampleAnalyzer()
        self._packs: Dict[str, StudioScenarioPack] = {}
        self._lock = threading.RLock()
        self.load_diagnostics: List[str] = []
        self._load()

    def home(self) -> Dict[str, Any]:
        capabilities = (
            self.generation_service.capabilities(include_runtime_health=False)
            if self.generation_service
            else {}
        )
        return {
            "creation_paths": [
                {
                    "id": CreationPath.EXISTING_SOURCES.value,
                    "title": "Use Existing Sources",
                    "description": "Build from the verified NetSpout catalog.",
                },
                {
                    "id": CreationPath.IMPORT_SANITIZED_SAMPLE.value,
                    "title": "Import Sanitized Sample",
                    "description": (
                        "Create a private custom source from telemetry you are "
                        "authorized to use."
                    ),
                },
                {
                    "id": CreationPath.CLONE_SCENARIO.value,
                    "title": "Clone Existing Scenario",
                    "description": (
                        "Preserve the telemetry contract while changing modeled state."
                    ),
                },
            ],
            "import_notice": (
                "Import only telemetry you are authorized to use. Remove "
                "credentials, secrets, customer identifiers and personal "
                "information before importing."
            ),
            "sources": capabilities.get("sources", []),
            "scenarios": capabilities.get("scenarios", []),
            "private_packs": [self._summary(item) for item in self.list_packs()],
        }

    def analyze_sample(
        self, request: SampleAnalysisRequest
    ) -> SampleAnalysisResult:
        return self.analyzer.analyze(request)

    def validate_custom_source(
        self, draft: CustomSourceDraft
    ) -> Dict[str, Any]:
        analysis = self.analyzer.analyze(
            SampleAnalysisRequest(
                sample=draft.sanitized_sample,
                authorization_acknowledged=True,
                format_hint=draft.format,
            )
        )
        errors = []
        if analysis.blocked:
            errors.append(
                "reviewed sample still contains sensitive or environment-specific values"
            )
        if analysis.sample_fingerprint != draft.analyzed_fingerprint:
            errors.append(
                "sample changed after analysis; analyze the sanitized value again"
            )
        if any(item.classification == FieldClassification.SENSITIVE for item in draft.fields):
            errors.append("sensitive fields cannot enter a custom source contract")
        return {
            "valid": not errors,
            "errors": errors,
            "privacy_status": analysis.privacy_status.value,
            "native_contract": {
                "format": draft.format,
                "structural_fields": [
                    item.name
                    for item in draft.fields
                    if item.classification == FieldClassification.STRUCTURAL
                ],
            },
            "splunk_contract": {
                "sourcetype": draft.netspout_sourcetype,
                "authority": (
                    "NETSPOUT_DEFINED" if draft.netspout_sourcetype else None
                ),
                "integration": "NOT ESTABLISHED",
                "cim": "CIM NOT ESTABLISHED",
            },
            "netspout_contract": {
                "modeled_fields": [
                    item.name
                    for item in draft.fields
                    if item.classification == FieldClassification.MODELED
                ],
                "unknown_fields": [
                    item.name
                    for item in draft.fields
                    if item.classification == FieldClassification.UNKNOWN
                ],
            },
        }

    def create_draft(self, request: StudioDraftRequest) -> StudioScenarioPack:
        if request.creation_path == CreationPath.CLONE_SCENARIO:
            if not request.clone_scenario_id:
                raise ValueError("clone path requires clone_scenario_id")
            return self.clone_scenario(request.clone_scenario_id)
        source_ids = list(dict.fromkeys(request.source_ids))
        correlated_native = {
            "ietf-snmpv2c-ifmib",
            "openconfig-gnmi-interfaces",
        }.issubset(set(source_ids))
        default_entity_id = (
            "cisco-asr9k-pe1" if correlated_native else "router-01.example"
        )
        return StudioScenarioPack(
            pack_id="private-{}".format(_slug(request.title)),
            scenario_id="studio-{}".format(_slug(request.title)),
            title=request.title,
            description="Private Scenario Studio draft.",
            story="A locally authored modeled scenario.",
            creation_path=request.creation_path,
            source_ids=source_ids,
            zones=[TopologyZone(zone_id="lab", label="Private Lab")],
            entities=[
                StudioEntity(
                    entity_id=default_entity_id,
                    label="Router 01",
                    entity_type="router",
                    zone_id="lab",
                    attributes={"address": "192.0.2.10"},
                )
            ],
            relationships=[],
            baseline=[
                StudioStateValue(
                    state_key="interface.status",
                    entity_id=default_entity_id,
                    value="UP",
                )
            ],
            timeline=[
                StudioTransition(
                    transition_id="baseline",
                    stage=ScenarioStage.BASELINE,
                    offset_seconds=0,
                    title="Baseline",
                    state_changes=[
                        StudioStateValue(
                            state_key="interface.status",
                            entity_id=default_entity_id,
                            value="UP",
                        )
                    ],
                    source_ids=source_ids,
                ),
                StudioTransition(
                    transition_id="incident",
                    stage=ScenarioStage.INCIDENT,
                    offset_seconds=300,
                    title="Incident",
                    state_changes=[
                        StudioStateValue(
                            state_key="interface.status",
                            entity_id=default_entity_id,
                            value="DOWN",
                        )
                    ],
                    source_ids=source_ids,
                ),
                StudioTransition(
                    transition_id="recovery",
                    stage=ScenarioStage.RECOVERY,
                    offset_seconds=600,
                    title="Recovery",
                    state_changes=[
                        StudioStateValue(
                            state_key="interface.status",
                            entity_id=default_entity_id,
                            value="UP",
                        )
                    ],
                    source_ids=source_ids,
                ),
            ],
            contract_fingerprints=self._contract_fingerprints(source_ids),
        )

    def clone_scenario(self, scenario_id: str) -> StudioScenarioPack:
        if not self.generation_service:
            raise ValueError("generation service is unavailable")
        scenario = next(
            (
                item
                for item in self.generation_service.capabilities(
                    include_runtime_health=False
                )["scenarios"]
                if item["scenario_id"] == scenario_id
            ),
            None,
        )
        if not scenario:
            raise ValueError("unknown scenario")
        entities = [
            StudioEntity(
                entity_id=item.get("entity_id") or item["node_id"],
                label=item.get("label") or item["node_id"],
                entity_type=item.get("role") or "generic",
                zone_id=item["zone_id"],
                attributes={
                    key: str(value)
                    for key, value in {
                        "vendor": item.get("vendor"),
                        "product": item.get("product"),
                    }.items()
                    if value
                },
            )
            for item in scenario["nodes"]
        ]
        relationships = [
            StudioRelationship(
                relationship_id=item["relationship_id"],
                source_entity_id=self._node_entity(
                    scenario["nodes"], item["source_node_id"]
                ),
                target_entity_id=self._node_entity(
                    scenario["nodes"], item["target_node_id"]
                ),
                relationship_type=item["relationship_type"],
                protocol=item.get("protocol"),
            )
            for item in scenario["relationships"]
        ]
        timeline = [
            StudioTransition(
                transition_id=item["step_id"],
                stage=ScenarioStage(item["stage"]),
                offset_seconds=index * 60,
                title=item["description"],
                state_changes=[],
                source_ids=item.get("evidence_source_ids", []),
            )
            for index, item in enumerate(scenario["timeline"])
        ]
        cloned_title = "{} — Private Clone".format(scenario["title"])
        return StudioScenarioPack(
            pack_id="private-{}-clone".format(_slug(scenario_id)),
            scenario_id="studio-{}-clone".format(_slug(scenario_id)),
            title=cloned_title,
            description=scenario["description"],
            story=scenario["story"],
            creation_path=CreationPath.CLONE_SCENARIO,
            source_ids=scenario["source_ids"],
            zones=[TopologyZone.model_validate(item) for item in scenario["zones"]],
            entities=entities,
            relationships=relationships,
            baseline=[],
            timeline=timeline,
            contract_fingerprints=self._contract_fingerprints(
                scenario["source_ids"]
            ),
            cloned_from_scenario_id=scenario_id,
        )

    def validate_pack(
        self, pack: StudioScenarioPack
    ) -> StudioValidationReport:
        checks: List[StudioValidationCheck] = []
        errors: List[str] = []
        warnings: List[str] = []
        capabilities = (
            self.generation_service.capabilities(include_runtime_health=False)
            if self.generation_service
            else {"sources": [], "scenarios": []}
        )
        available_sources = {
            item["source_id"]: item for item in capabilities.get("sources", [])
        }
        available_sources.update(
            {
                item.source_id: {"source_id": item.source_id}
                for item in pack.custom_sources
            }
        )
        custom_ids = {item.source_id for item in pack.custom_sources}

        def record(check_id: str, passed: bool, detail: str) -> None:
            checks.append(
                StudioValidationCheck(
                    check_id=check_id,
                    state="PASS" if passed else "FAIL",
                    detail=detail,
                )
            )
            if not passed:
                errors.append(detail)

        record(
            "sources",
            bool(pack.source_ids)
            and all(item in available_sources for item in pack.source_ids),
            "Every selected source must exist in the catalog or this private pack.",
        )
        record(
            "source-path-boundary",
            not custom_ids or set(pack.source_ids).issubset(custom_ids),
            (
                "Phase 6 custom-source scenarios cannot mix imported contracts "
                "with catalog-native bindings in one destination execution."
            ),
        )
        record(
            "custom-source-cardinality",
            len(custom_ids) <= 1,
            (
                "Phase 6 executes exactly one imported custom source per "
                "private scenario."
            ),
        )
        executable_errors = []
        if self.generation_service:
            for source_id in pack.source_ids:
                if source_id in custom_ids:
                    continue
                try:
                    self._existing_binding(source_id)
                except ValueError as exc:
                    executable_errors.append(str(exc))
        record(
            "executable-bindings",
            not executable_errors,
            (
                "; ".join(executable_errors)
                if executable_errors
                else "Every catalog source has an executable validated binding."
            ),
        )
        entity_ids = {item.entity_id for item in pack.entities}
        zone_ids = {item.zone_id for item in pack.zones}
        record(
            "entities",
            bool(entity_ids)
            and len(entity_ids) == len(pack.entities)
            and all(item.zone_id in zone_ids for item in pack.entities),
            "Entity identifiers must be unique and reference declared zones.",
        )
        record(
            "relationships",
            all(
                item.source_entity_id in entity_ids
                and item.target_entity_id in entity_ids
                for item in pack.relationships
            ),
            "Topology relationships must reference declared entities.",
        )
        offsets = [item.offset_seconds for item in pack.timeline]
        record(
            "timeline",
            bool(pack.timeline)
            and offsets == sorted(offsets)
            and len(set(offsets)) == len(offsets),
            "Timeline offsets must be unique and chronological.",
        )
        state_errors = []
        custom_by_id = {item.source_id: item for item in pack.custom_sources}
        for transition in pack.timeline:
            if any(item not in pack.source_ids for item in transition.source_ids):
                state_errors.append(
                    "{} references an unselected source".format(
                        transition.transition_id
                    )
                )
            for value in transition.state_changes:
                if value.entity_id not in entity_ids:
                    state_errors.append(
                        "{} references missing entity {}".format(
                            transition.transition_id, value.entity_id
                        )
                    )
                for source_id in transition.source_ids:
                    if source_id in custom_by_id:
                        modeled = {
                            item.name for item in custom_by_id[source_id].fields
                            if item.classification
                            in {
                                FieldClassification.MODELED,
                                FieldClassification.DERIVED,
                                FieldClassification.CORRELATION,
                            }
                        }
                        if value.state_key not in modeled:
                            state_errors.append(
                                "{} cannot express state {}".format(
                                    source_id, value.state_key
                                )
                            )
                    elif value.state_key not in _SAFE_STATE_INPUTS.get(
                        source_id, set()
                    ):
                        state_errors.append(
                            "{} cannot express state {}".format(
                                source_id, value.state_key
                            )
                        )
        record(
            "state-compatibility",
            not state_errors,
            "; ".join(state_errors)
            if state_errors
            else "Every state change is supported by its selected generators.",
        )
        parameter_errors = []
        for parameter in pack.parameters:
            error = parameter.validate_value(parameter.default)
            if error:
                parameter_errors.append(
                    "{} {}".format(parameter.parameter_id, error)
                )
            for custom in pack.custom_sources:
                field = next(
                    (
                        item
                        for item in custom.fields
                        if item.name == parameter.state_key
                    ),
                    None,
                )
                if field and field.classification == FieldClassification.STRUCTURAL:
                    parameter_errors.append(
                        "{} cannot alter structural field {}".format(
                            parameter.parameter_id, parameter.state_key
                        )
                    )
        record(
            "parameters",
            not parameter_errors,
            "; ".join(parameter_errors)
            if parameter_errors
            else "Parameter defaults satisfy declared constraints.",
        )
        record(
            "privacy",
            pack.privacy_status == PrivacyStatus.SANITIZED
            and all(
                self.validate_custom_source(item)["valid"]
                for item in pack.custom_sources
            ),
            "All imported samples must pass local privacy review.",
        )
        record(
            "provenance",
            bool(pack.provenance) and bool(pack.redistribution),
            "Privacy, provenance and redistribution must be declared separately.",
        )
        current_fingerprints = self._contract_fingerprints(
            [item for item in pack.source_ids if item not in custom_by_id]
        )
        record(
            "contract-integrity",
            all(
                pack.contract_fingerprints.get(source_id) == value
                for source_id, value in current_fingerprints.items()
            ),
            "Verified source contracts must remain unchanged.",
        )
        mapping_sources = {item.source_id for item in pack.correlation_mappings}
        if len(pack.source_ids) > 1 and not mapping_sources.issuperset(
            set(pack.source_ids)
        ):
            warnings.append(
                "Multi-source drafts should map each source to common entity identities."
            )
        investigation_errors = [
            item.investigation_id
            for item in pack.investigations
            if item.portability == SplPortability.PRODUCTION_PORTABLE
            and item.netspout_only_fields
        ]
        record(
            "investigations",
            not investigation_errors,
            (
                "Production-portable SPL cannot depend on NetSpout-only fields: "
                + ", ".join(investigation_errors)
                if investigation_errors
                else "Investigation portability declarations are consistent."
            ),
        )
        ceiling = (
            StudioMaturity.STRUCTURE_VALIDATED
            if not errors
            else StudioMaturity.DRAFT
        )
        return StudioValidationReport(
            valid=not errors,
            maturity_ceiling=ceiling,
            checks=checks,
            errors=errors,
            warnings=warnings,
        )

    def save_pack(self, pack: StudioScenarioPack) -> StudioScenarioPack:
        with self._lock:
            report = self.validate_pack(pack)
            if not report.valid:
                raise ValueError(
                    "scenario pack validation failed: {}".format(
                        "; ".join(report.errors)
                    )
                )
            timestamp = _now()
            existing = self._packs.get(pack.pack_id)
            stored = pack.model_copy(
                update={
                    "maturity": report.maturity_ceiling,
                    "created_at": existing.created_at if existing else timestamp,
                    "updated_at": timestamp,
                }
            )
            path = self._path(stored.pack_id)
            payload = stored.model_dump_json(indent=2)
            fd, temporary = tempfile.mkstemp(
                prefix=".{}.".format(stored.pack_id),
                suffix=".tmp",
                dir=str(self.storage_dir),
                text=True,
            )
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                self._register(stored)
                try:
                    os.replace(temporary, path)
                except Exception:
                    if self.generation_service:
                        self.generation_service.unregister_private_pack(
                            stored.pack_id, stored.scenario_id
                        )
                        if existing:
                            self._register(existing)
                    raise
                try:
                    path.chmod(0o600)
                except OSError:
                    pass
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            self._packs[stored.pack_id] = stored
            return stored

    def list_packs(self) -> List[StudioScenarioPack]:
        return sorted(self._packs.values(), key=lambda item: item.updated_at or "")

    def summarize(self, pack: StudioScenarioPack) -> Dict[str, Any]:
        return self._summary(pack)

    def get_pack(self, pack_id: str) -> Optional[StudioScenarioPack]:
        return self._packs.get(pack_id)

    def delete_pack(self, pack_id: str) -> bool:
        with self._lock:
            pack = self._packs.get(pack_id)
            if not pack:
                return False
            if self.generation_service:
                self.generation_service.unregister_private_pack(
                    pack.pack_id, pack.scenario_id
                )
            path = self._path(pack_id)
            if path.exists():
                path.unlink()
            self._packs.pop(pack_id, None)
            return True

    def export_gate(self, pack_id: str, public: bool = False) -> Dict[str, Any]:
        pack = self._require_pack(pack_id)
        report = self.validate_pack(pack)
        blockers = list(report.errors)
        if public:
            if pack.redistribution != RedistributionStatus.REDISTRIBUTION_PERMITTED:
                blockers.append("public export requires established redistribution permission")
            if pack.provenance == SampleProvenance.UNKNOWN_ORIGIN:
                blockers.append("public export requires established provenance")
            if pack.custom_sources:
                blockers.append(
                    "Phase 6 does not publish imported custom source packs"
                )
        return {
            "allowed": not blockers,
            "scope": "PUBLIC" if public else "LOCAL_PRIVATE",
            "blockers": blockers,
            "sensitive_scan": "PASS" if not blockers else "BLOCKED",
        }

    def compile_pack(
        self, pack: StudioScenarioPack
    ) -> Tuple[PackDefinition, CompositionDefinition]:
        report = self.validate_pack(pack)
        if not report.valid:
            raise ValueError("cannot compile an invalid Studio pack")
        custom_by_id = {item.source_id: item for item in pack.custom_sources}
        source_entries: List[SourcePackEntry] = []
        generators: List[GeneratorDefinition] = []
        validators: List[ValidatorDefinition] = []
        transports: List[TransportCapability] = []
        destinations: List[DestinationDefinition] = []
        evidence: List[EvidenceReference] = []
        bindings: List[SourceBinding] = []

        for source_id in pack.source_ids:
            custom = custom_by_id.get(source_id)
            if custom:
                evidence_id = "evid-{}-private-sample".format(source_id)
                generator_id = "generator-{}-private-template".format(source_id)
                validator_id = "validator-{}-private-structure".format(source_id)
                transport_id = "transport-{}-private-hec".format(source_id)
                destination_id = "destination-{}-private-splunk".format(source_id)
                evidence.append(
                    EvidenceReference(
                        evidence_id=evidence_id,
                        title="Reviewed local private sample fingerprint",
                        publisher="Scenario Studio user",
                        reference="local-private://{}".format(
                            custom.analyzed_fingerprint
                        ),
                        provenance=ProvenanceClassification.NETSPOUT_SCHEMA,
                        verification_state=VerificationState.PARTIALLY_VERIFIED,
                        notes=(
                            "The original sample is not embedded in evidence or "
                            "published. Privacy review does not establish ownership."
                        ),
                    )
                )
                telemetry_source = self._custom_telemetry_source(
                    custom, pack.scenario_id, evidence_id
                )
                source_entries.append(
                    SourcePackEntry(
                        source=telemetry_source,
                        generator_ids=[generator_id],
                        validator_ids=[validator_id],
                        compatible_transport_ids=[transport_id],
                        raw_fidelity=RawFidelityPolicy(
                            preserve_native_raw=True
                        ),
                        custom_lifecycle=CustomSourceLifecycle.DRAFT,
                        sample_derived=True,
                        promotion_authority=PromotionAuthority.HUMAN_REVIEW_REQUIRED,
                    )
                )
                generators.append(
                    GeneratorDefinition(
                        generator_id=generator_id,
                        implementation_ref=(
                            "netspout_core.scenario_studio."
                            "build_private_template_generator"
                        ),
                        source_ids=[source_id],
                        signals=[TelemetrySignal.EVENTS],
                        verification_state=VerificationState.PARTIALLY_VERIFIED,
                        evidence_ids=[evidence_id],
                    )
                )
                validators.append(
                    ValidatorDefinition(
                        validator_id=validator_id,
                        implementation_ref=(
                            "netspout_core.scenario_studio."
                            "build_private_template_validator"
                        ),
                        source_ids=[source_id],
                        stages=[
                            ValidationStage.RAW_VERIFIED,
                            ValidationStage.SENT,
                            ValidationStage.SPLUNK_OBSERVED,
                        ],
                        evidence_ids=[evidence_id],
                    )
                )
                transports.append(
                    TransportCapability(
                        transport_id=transport_id,
                        component="NetSpout private custom-source HEC adapter",
                        protocol="HEC",
                        signals=[TelemetrySignal.EVENTS],
                        compatible_source_ids=[source_id],
                        verification_state=VerificationState.PARTIALLY_VERIFIED,
                        implemented=True,
                        evidence_ids=[evidence_id],
                        notes=(
                            "NETSPOUT-DEFINED private ingestion path; it is not "
                            "the vendor source's native transport."
                        ),
                    )
                )
                destinations.append(
                    DestinationDefinition(
                        destination_id=destination_id,
                        destination_type="LOCAL_PRIVATE_SPLUNK",
                        accepted_transport_ids=[transport_id],
                        verification_state=VerificationState.PARTIALLY_VERIFIED,
                        evidence_ids=[evidence_id],
                    )
                )
                bindings.append(
                    SourceBinding(
                        source_id=source_id,
                        generator_id=generator_id,
                        transport_id=transport_id,
                        destination_transport_id=transport_id,
                        destination_id=destination_id,
                        validator_ids=[validator_id],
                    )
                )
            else:
                bindings.append(self._existing_binding(source_id))

        scenario = self._guided_manifest(pack)
        investigations = [self._investigation(item) for item in pack.investigations]
        definition = PackDefinition(
            pack_id=pack.pack_id,
            pack_version="0.1.0",
            kind=PackKind.SCENARIO,
            display_name=pack.title,
            maturity=PackMaturity.DRAFT,
            verification_state=VerificationState.PARTIALLY_VERIFIED,
            evidence=evidence,
            sources=source_entries,
            generators=generators,
            validators=validators,
            transports=transports,
            destinations=destinations,
            scenarios=[scenario],
            investigations=investigations,
        )
        composition = CompositionDefinition(
            composition_id="compose-{}".format(pack.scenario_id),
            scenario_id=pack.scenario_id,
            pack_ids=[pack.pack_id],
            source_bindings=bindings,
            investigation_recipe_ids=[
                item.recipe_id for item in investigations
            ],
        )
        return definition, composition

    def _register(self, pack: StudioScenarioPack) -> None:
        if not self.generation_service:
            return
        definition, composition = self.compile_pack(pack)
        custom_generators = {}
        custom_validators = {}
        search_scopes = {}
        generation_module = sys.modules[
            self.generation_service.__class__.__module__
        ]
        generated_event_type = generation_module.GeneratedEvent
        for custom in pack.custom_sources:
            generator_id = "generator-{}-private-template".format(custom.source_id)
            validator_id = "validator-{}-private-structure".format(custom.source_id)
            custom_generators[generator_id] = build_private_template_generator(
                custom, pack, generated_event_type
            )
            custom_validators[validator_id] = build_private_template_validator(
                custom
            )
            if custom.netspout_sourcetype:
                search_scopes[custom.source_id] = (
                    "idx_network_ops",
                    custom.netspout_sourcetype,
                )
        self.generation_service.register_private_pack(
            definition,
            composition,
            generator_adapters=custom_generators,
            validator_adapters=custom_validators,
            search_scopes=search_scopes,
        )

    def _load(self) -> None:
        for path in self.storage_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                pack = StudioScenarioPack.model_validate(payload)
                self._packs[pack.pack_id] = pack
                self._register(pack)
            except Exception:
                # A corrupt private pack must not block application startup.
                self.load_diagnostics.append(
                    "{} could not be loaded and remains fail-closed".format(path.name)
                )
                continue

    def _path(self, pack_id: str) -> Path:
        return self.storage_dir / "{}.json".format(pack_id)

    def _require_pack(self, pack_id: str) -> StudioScenarioPack:
        pack = self.get_pack(pack_id)
        if not pack:
            raise KeyError(pack_id)
        return pack

    def _contract_fingerprints(self, source_ids: Iterable[str]) -> Dict[str, str]:
        result = {}
        for source_id in source_ids:
            source = self.catalog.get_telemetry_source(source_id)
            if source:
                contract = {
                    "native_contract": source["native_contract"],
                    "splunk_contract": source["splunk_contract"],
                    "netspout_structural_fields": source["netspout_contract"][
                        "structural_fields"
                    ],
                }
                result[source_id] = _fingerprint(
                    json.dumps(contract, sort_keys=True, separators=(",", ":"))
                )
        return result

    def _existing_binding(self, source_id: str) -> SourceBinding:
        candidates = [
            binding
            for composition in self.generation_service.registry.compositions
            for binding in composition.source_bindings
            if binding.source_id == source_id
        ]
        if not candidates:
            raise ValueError(
                "source {} has no executable Phase 5 binding".format(source_id)
            )
        candidates.sort(key=lambda item: not bool(item.runtime_adapter_ref))
        return deepcopy(candidates[0])

    def _guided_manifest(
        self, pack: StudioScenarioPack
    ) -> GuidedScenarioManifest:
        entity_ids = {item.entity_id for item in pack.entities}
        nodes = [
            TopologyNode(
                node_id=item.entity_id,
                technology_id="studio-{}".format(item.entity_type),
                zone_id=item.zone_id,
                role=item.entity_type,
                source_ids=[
                    source_id
                    for source_id in pack.source_ids
                    if any(
                        mapping.source_id == source_id
                        and mapping.entity_id == item.entity_id
                        for mapping in pack.correlation_mappings
                    )
                ],
                label=item.label,
                entity_id=item.entity_id,
                description="Scenario Studio modeled entity",
            )
            for item in pack.entities
        ]
        relationships = [
            TopologyRelationship(
                relationship_id=item.relationship_id,
                source_node_id=item.source_entity_id,
                target_node_id=item.target_entity_id,
                relationship_type=item.relationship_type,
                protocol=item.protocol,
                telemetry_source_ids=[
                    mapping.source_id
                    for mapping in pack.correlation_mappings
                    if mapping.entity_id
                    in {item.source_entity_id, item.target_entity_id}
                ],
            )
            for item in pack.relationships
        ]
        observer = "studio-splunk"
        if observer not in entity_ids:
            nodes.append(
                TopologyNode(
                    node_id=observer,
                    technology_id="splunk-enterprise",
                    zone_id=pack.zones[0].zone_id,
                    role="observer",
                    label="Splunk",
                    entity_id=observer,
                )
            )
            entity_ids.add(observer)
        producer = next(
            (item.entity_id for item in pack.entities if item.entity_type != "observer"),
            pack.entities[0].entity_id,
        )
        telemetry_paths = [
            TelemetryPath(
                path_id="path-{}".format(source_id),
                source_id=source_id,
                producer_node_id=producer,
                observer_node_id=observer,
                label=source_id,
            )
            for source_id in pack.source_ids
        ]
        timeline = [
            TimelineStep(
                step_id=item.transition_id,
                stage=item.stage,
                description=item.title,
                state_changes={
                    value.state_key: str(value.value)
                    for value in item.state_changes
                },
                entity_state_changes={
                    value.entity_id: "{}={}".format(
                        value.state_key, value.value
                    )
                    for value in item.state_changes
                },
                telemetry_state_changes={
                    source_id: item.title for source_id in item.source_ids
                },
                expected_observations=[
                    "{} reflects {}".format(source_id, item.title)
                    for source_id in item.source_ids
                ],
                evidence_source_ids=item.source_ids,
                incident_ids=(
                    ["studio-incident"]
                    if item.stage
                    in {
                        ScenarioStage.PRECURSOR,
                        ScenarioStage.INCIDENT,
                        ScenarioStage.IMPACT,
                        ScenarioStage.DETECTION,
                    }
                    else []
                ),
            )
            for item in pack.timeline
        ]
        incident_sources = list(dict.fromkeys(pack.source_ids))
        incidents = (
            [
                IncidentEvidence(
                    incident_id="studio-incident",
                    source_ids=incident_sources,
                    assertion="Selected telemetry derives from one modeled state.",
                    corroboration_required=len(incident_sources) > 1,
                )
            ]
            if incident_sources
            else []
        )
        return GuidedScenarioManifest(
            scenario_id=pack.scenario_id,
            title=pack.title,
            description=pack.description,
            story=pack.story,
            domain="netops",
            category="PRIVATE_STUDIO",
            technical_description=(
                "A private Scenario Studio draft. Contracts remain immutable; "
                "timeline values are modeled."
            ),
            difficulty="CUSTOM",
            expected_duration_minutes=max(
                1,
                int(
                    max(item.offset_seconds for item in pack.timeline) / 60
                ),
            ),
            learning_objectives=["Validate a locally authored telemetry scenario."],
            business_impact="Modeled private lab impact.",
            prerequisites=["Local NetSpout runtime", "Configured Splunk destination"],
            technology_ids=sorted(
                {"studio-{}".format(item.entity_type) for item in pack.entities}
            ),
            source_ids=pack.source_ids,
            entities=sorted(entity_ids),
            zones=pack.zones,
            nodes=nodes,
            relationships=relationships,
            telemetry_paths=telemetry_paths,
            incident_path=[producer, observer],
            runtime_state_keys=sorted(
                {
                    value.state_key
                    for transition in pack.timeline
                    for value in transition.state_changes
                }
            ),
            timeline=timeline,
            incidents=incidents,
            parameters=[
                ScenarioParameter(
                    parameter_id=item.parameter_id,
                    value_type=item.value_type,
                    changes_modeled_values_only=True,
                )
                for item in pack.parameters
            ],
            expected_evidence=[
                "GENERATED",
                "SPLUNK_DISPATCHED",
                "SPLUNK_OBSERVED",
            ],
            investigation_recipe_ids=[
                item.investigation_id for item in pack.investigations
            ],
            investigation_steps=[
                GuidedInvestigationStep(
                    step_id="step-{}".format(item.investigation_id),
                    recipe_id=item.investigation_id,
                    title=item.title,
                    question=item.question,
                    expected_finding=item.expected_finding,
                    explanation=item.explanation,
                    source_ids=item.evidence_source_ids,
                )
                for item in pack.investigations
            ],
            validation_expectations=[
                ScenarioValidationExpectation(
                    validation_id="validate-{}-observed".format(source_id),
                    label="{} observed".format(source_id),
                    evidence_stage="SPLUNK_OBSERVED",
                    expected_state="PROVEN",
                    requirement=ValidationRequirement.REQUIRED,
                    source_id=source_id,
                )
                for source_id in pack.source_ids
            ],
            visualization=ScenarioVisualization(
                mode=VisualizationMode.AUTOMATIC
            ),
            replay_policy=ReplayPolicy(),
            troubleshooting_steps=[
                "Review source-specific evidence before treating the run as successful."
            ],
            production_replication_guidance=[
                "Private Studio packs are lab artifacts, not production compatibility claims."
            ],
        )

    @staticmethod
    def _investigation(item: StudioInvestigation) -> InvestigationRecipe:
        return InvestigationRecipe(
            recipe_id=item.investigation_id,
            title=item.title,
            objective=item.objective,
            question=item.question,
            expected_finding=item.expected_finding,
            explanation=item.explanation,
            portability=item.portability,
            spl=item.spl,
            source_ids=item.evidence_source_ids,
            netspout_only_fields=item.netspout_only_fields,
        )

    @staticmethod
    def _custom_telemetry_source(
        custom: CustomSourceDraft, scenario_id: str, evidence_id: str
    ) -> TelemetrySource:
        structural = [
            item.name
            for item in custom.fields
            if item.classification == FieldClassification.STRUCTURAL
        ]
        modeled = [
            item.name
            for item in custom.fields
            if item.classification == FieldClassification.MODELED
        ]
        sourcetypes = (
            [
                SourcetypeClaim(
                    name=custom.netspout_sourcetype,
                    authority=SourcetypeAuthority.NETSPOUT_DEFINED,
                    evidence_ids=[evidence_id],
                )
            ]
            if custom.netspout_sourcetype
            else []
        )
        return TelemetrySource(
            source_id=custom.source_id,
            vendor="Private custom source",
            product=custom.display_name,
            product_family="Scenario Studio",
            domains=["custom"],
            telemetry_source=custom.source_description,
            verification_state=VerificationState.PARTIALLY_VERIFIED,
            provenance=[
                ProvenanceClassification.RESEARCH_REQUIRED,
                ProvenanceClassification.MODELED_VALUE,
            ],
            evidence_ids=[evidence_id],
            native_contract=NativeContract(
                contract_id="native-{}".format(custom.source_id),
                verification_state=VerificationState.PARTIALLY_VERIFIED,
                format=custom.format,
                native_schema="User-reviewed private sample structure",
                transports=[
                    TransportDefinition(protocol="PRIVATE_SAMPLE", encoding=custom.format)
                ],
                structural_fields=structural,
                evidence_ids=[evidence_id],
            ),
            splunk_contract=SplunkContract(
                contract_id="splunk-{}".format(custom.source_id),
                verification_state=(
                    VerificationState.PARTIALLY_VERIFIED
                    if sourcetypes
                    else VerificationState.RESEARCH_REQUIRED
                ),
                input_mechanisms=(
                    ["NetSpout private structured ingestion"]
                    if sourcetypes
                    else []
                ),
                sourcetypes=sourcetypes,
                evidence_ids=[evidence_id] if sourcetypes else [],
            ),
            netspout_contract=NetSpoutContract(
                contract_id="netspout-{}".format(custom.source_id),
                verification_state=VerificationState.PARTIALLY_VERIFIED,
                schema_classification=ProvenanceClassification.MODELED_VALUE,
                generator=(
                    "netspout_core.scenario_studio."
                    "build_private_template_generator"
                ),
                validator=(
                    "netspout_core.scenario_studio."
                    "build_private_template_validator"
                ),
                transports=["PRIVATE_SAMPLE_TO_HEC"],
                modeled_fields=modeled,
                structural_fields=structural,
                scenario_ids=[scenario_id],
                generation_modes=["MODE_A", "MODE_B", "MODE_D"],
                runtime_status="AVAILABLE",
                maturity="DRAFT",
                evidence_ids=[evidence_id],
            ),
            spl_field_scope=SplFieldScope(
                production_fields=[],
                netspout_only_fields=[
                    "netspout_run_id",
                    "netspout_scenario_id",
                    "netspout_phase",
                ],
                portable_spl_status=VerificationState.RESEARCH_REQUIRED,
            ),
            known_limitations=[
                "Imported sample meaning is not vendor verified.",
                "Splunk integration and CIM mapping are not established.",
                "The source remains private/local unless rights are established.",
            ],
        )

    @staticmethod
    def _node_entity(nodes: List[Dict[str, Any]], node_id: str) -> str:
        node = next(item for item in nodes if item["node_id"] == node_id)
        return node.get("entity_id") or node_id

    @staticmethod
    def _summary(pack: StudioScenarioPack) -> Dict[str, Any]:
        return {
            "pack_id": pack.pack_id,
            "scenario_id": pack.scenario_id,
            "title": pack.title,
            "maturity": pack.maturity.value,
            "privacy_status": pack.privacy_status.value,
            "provenance": pack.provenance.value,
            "redistribution": pack.redistribution.value,
            "source_count": len(pack.source_ids),
            "custom_source_count": len(pack.custom_sources),
            "updated_at": pack.updated_at,
        }


def build_private_template_validator(custom: CustomSourceDraft):
    structural = {
        item.name: item
        for item in custom.fields
        if item.classification == FieldClassification.STRUCTURAL
    }

    def validate(raw: str) -> bool:
        try:
            parsed = json.loads(raw) if custom.format.upper().startswith("JSON") else {}
        except json.JSONDecodeError:
            return False
        if structural and not isinstance(parsed, dict):
            return False
        return all(name in parsed for name in structural)

    return validate


def build_private_template_generator(
    custom: CustomSourceDraft,
    pack: StudioScenarioPack,
    generated_event_type: Optional[Any] = None,
):
    records, _, _ = SampleAnalyzer._records(custom.sanitized_sample, custom.format)
    template = records[0]
    fields = {item.name: item for item in custom.fields}
    timeline_by_stage = {
        item.stage.value: item for item in pack.timeline
    }
    parameters = {item.parameter_id: item for item in pack.parameters}

    def generate(
        *,
        run_id: str,
        phase: str,
        ordinal: int,
        event_family: str,
        scenario_parameters: Optional[Dict[str, Any]] = None,
    ):
        if generated_event_type is None:
            from netspout_core.unified_generation import GeneratedEvent

            event_type = GeneratedEvent
        else:
            event_type = generated_event_type

        payload = deepcopy(template)
        transition = timeline_by_stage.get(phase)
        if transition:
            for change in transition.state_changes:
                field = fields.get(change.state_key)
                if field and field.classification != FieldClassification.STRUCTURAL:
                    payload[change.state_key] = change.value
        for parameter_id, value in (scenario_parameters or {}).items():
            parameter = parameters.get(parameter_id)
            if not parameter:
                continue
            error = parameter.validate_value(value)
            if error:
                raise ValueError("{} {}".format(parameter_id, error))
            field = fields.get(parameter.state_key)
            if field and field.classification == FieldClassification.STRUCTURAL:
                raise ValueError("scenario parameters cannot alter structural fields")
            payload[parameter.state_key] = value
        payload["netspout_run_id"] = run_id
        payload["netspout_scenario_id"] = pack.scenario_id
        payload["netspout_phase"] = phase
        event_id = hashlib.sha256(
            "{}:{}:{}:{}".format(run_id, custom.source_id, phase, ordinal).encode(
                "utf-8"
            )
        ).hexdigest()[:24]
        payload["netspout_event_id"] = event_id
        raw = (
            json.dumps(payload, sort_keys=True, separators=(",", ":"))
            if custom.format.upper().startswith("JSON")
            else " ".join(
                "{}={}".format(key, json.dumps(value))
                for key, value in sorted(payload.items())
            )
        )
        return event_type(
            event_id=event_id,
            source_id=custom.source_id,
            contract_id="native-{}".format(custom.source_id),
            provenance=[
                "RESEARCH_REQUIRED",
                "MODELED_VALUE",
                "PRIVATE_LOCAL",
            ],
            transport_id="transport-{}-private-hec".format(custom.source_id),
            sourcetype=custom.netspout_sourcetype or "SOURCETYPE_RESEARCH_REQUIRED",
            sourcetype_authority=(
                "NETSPOUT_DEFINED"
                if custom.netspout_sourcetype
                else "RESEARCH_REQUIRED"
            ),
            phase=phase,
            raw=raw,
        )

    return generate


def max_maturity(
    requested: StudioMaturity, ceiling: StudioMaturity
) -> StudioMaturity:
    order = list(StudioMaturity)
    return order[min(order.index(requested), order.index(ceiling))]


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (normalized or "draft")[:60]
