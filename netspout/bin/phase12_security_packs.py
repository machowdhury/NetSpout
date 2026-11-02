# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/phase12_security_packs.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Phase 12 Agentic AI and software supply-chain security packs.

The runtime is intentionally an offline audit-event simulator. Protocol-shaped
fields are kept in ``protocol``; instrumentation fields are kept in ``audit``;
NetSpout correlation metadata is kept in ``scenario``. Nothing in this module
contacts an MCP/A2A peer, repository, registry, CI system, or model provider.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Tuple
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict


class Phase12GeneratedEvent(BaseModel):
    """Structural match for the orchestration service's generated-event view."""

    model_config = ConfigDict(extra="forbid")
    event_id: str
    source_id: str
    contract_id: str
    provenance: List[str]
    transport_id: str
    sourcetype: str
    sourcetype_authority: str
    phase: str
    raw: str


AGENT_PACK_ID = "netspout-phase12-agentic-ai-security"
SUPPLY_PACK_ID = "netspout-phase12-software-supply-chain"
CROSS_PACK_ID = "netspout-phase12-cross-domain"
SOURCE_CONFIG = {
    "phase12-agentic-audit": {
        "generator": "generator-phase12-agentic-audit",
        "validator": "validator-phase12-agentic-audit",
        "sourcetype": "netspout:phase12:agentic",
        "product": "Agentic AI Security Audit",
        "family": "MCP and A2A instrumentation",
        "evidence": ["EVID-P12-MCP-TOOLS", "EVID-P12-MCP-RESOURCES", "EVID-P12-MCP-AUTH", "EVID-P12-A2A", "EVID-P12-OWASP-AGENTIC", "EVID-P12-RUNTIME"],
    },
    "phase12-supply-chain-audit": {
        "generator": "generator-phase12-supply-chain-audit",
        "validator": "validator-phase12-supply-chain-audit",
        "sourcetype": "netspout:phase12:supply_chain",
        "product": "Software Supply Chain Security Audit",
        "family": "Repository, CI, provenance, and artifact instrumentation",
        "evidence": ["EVID-P12-SLSA", "EVID-P12-RUNTIME"],
    },
    "phase12-cross-domain-audit": {
        "generator": "generator-phase12-cross-domain-audit",
        "validator": "validator-phase12-cross-domain-audit",
        "sourcetype": "netspout:phase12:cross_domain",
        "product": "Cross-Domain Causal Audit",
        "family": "Agent, supply chain, infrastructure, and application instrumentation",
        "evidence": ["EVID-P12-MCP-TOOLS", "EVID-P12-SLSA", "EVID-P12-RUNTIME"],
    },
}

PHASES: Tuple[str, ...] = ("BASELINE", "PRECURSOR", "INCIDENT", "DETECTION", "RECOVERY")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SECRET_KEYS = re.compile(r"(password|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|private[_-]?key)", re.I)
_ALLOWED_PARAMETERS = {
    "seed",
    "intensity",
    "decision",
    "policy_mode",
    "peer_count",
    "entity_id",
    "studio_shared_state",
    "reference_scenario_id",
}


@dataclass(frozen=True)
class Phase12StatePlan:
    """One deterministic state graph and clock shared by a Phase 12 run."""

    run_id: str
    scenario_id: str
    seed: int
    clock: Any
    entities: Tuple[Mapping[str, str], ...]
    relationships: Tuple[Mapping[str, str], ...]
    correlation_id: str

    def timestamp_ns(self, phase: str) -> int:
        try:
            return dict(self.clock.phase_timestamps_ns)[phase]
        except KeyError as exc:
            raise ValueError("unknown Phase 12 clock phase") from exc


def build_phase12_state_plan(run_id: str, scenario_id: str, seed: int) -> Phase12StatePlan:
    """Create stable synthetic identities and a single immutable causal graph."""

    # Lazy import avoids catalog initialization cycles while reusing the
    # established immutable SimulationClock implementation at execution time.
    from netspout_core.native_runtime import SimulationClock

    if not _SAFE_ID.fullmatch(run_id) or not _SAFE_ID.fullmatch(scenario_id):
        raise ValueError("run and scenario identifiers must be bounded safe identifiers")
    base = 1_800_000_000_000_000_000 + (seed % 10_000) * 1_000_000
    clock = SimulationClock(tuple((phase, base + index * 1_000_000_000) for index, phase in enumerate(PHASES)))
    prefix = hashlib.sha256(f"{scenario_id}:{seed}".encode()).hexdigest()[:12]
    domain = "agentic" if scenario_id.startswith("AI-") else "supply-chain"
    if scenario_id.startswith("P12-XD-"):
        domain = "cross-domain"
    entities = (
        {"entity_id": f"agent-{prefix}", "entity_type": "ai-agent", "domain": domain},
        {"entity_id": f"resource-{prefix}", "entity_type": "synthetic-resource", "domain": domain},
        {"entity_id": f"policy-{prefix}", "entity_type": "security-policy", "domain": domain},
        {"entity_id": f"analytics-{prefix}", "entity_type": "splunk-lab", "domain": domain},
    )
    relationships = (
        {"relationship_id": f"request-{prefix}", "source_entity_id": entities[0]["entity_id"], "target_entity_id": entities[1]["entity_id"], "relationship_type": "requests"},
        {"relationship_id": f"evaluate-{prefix}", "source_entity_id": entities[2]["entity_id"], "target_entity_id": entities[0]["entity_id"], "relationship_type": "evaluates"},
        {"relationship_id": f"observe-{prefix}", "source_entity_id": entities[0]["entity_id"], "target_entity_id": entities[3]["entity_id"], "relationship_type": "observed-by"},
    )
    return Phase12StatePlan(
        run_id=run_id,
        scenario_id=scenario_id,
        seed=seed,
        clock=clock,
        entities=entities,
        relationships=relationships,
        correlation_id=f"p12-{prefix}",
    )


def extend_registry(base_registry: Dict[str, Any], specification: Dict[str, Any]) -> Dict[str, Any]:
    registry = deepcopy(base_registry)
    registry["registry_version"] = specification["registry_version"]
    references = specification["references"]
    phase12_source_ids = sorted({item["source"] for item in references})
    for pack in registry["packs"]:
        for transport in pack.get("transports", []):
            if transport["transport_id"] == "transport-local-hec":
                transport["compatible_source_ids"] = sorted(
                    set(transport.get("compatible_source_ids", []))
                    | set(phase12_source_ids)
                )
    groups = (
        (AGENT_PACK_ID, "AGENTIC_AI", [item for item in references if item["scenario_id"].startswith("AI-")]),
        (SUPPLY_PACK_ID, "SOFTWARE_SUPPLY_CHAIN", [item for item in references if item["scenario_id"].startswith("SC-")]),
        (CROSS_PACK_ID, "CROSS_DOMAIN", [item for item in references if item["scenario_id"].startswith("P12-XD-")]),
    )
    evidence = [_evidence(item) for item in specification["evidence"]]
    for pack_id, kind, items in groups:
        registry["packs"].append(_pack(pack_id, kind, items, evidence))
        registry["compositions"].extend(_composition(pack_id, item) for item in items)
    return registry


def _evidence(item: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "evidence_id": item["evidence_id"],
        "title": item["title"],
        "publisher": item["publisher"],
        "reference": item["reference"],
        "provenance": "NETSPOUT_SCHEMA" if item["publisher"] == "NetSpout" else "STANDARD_DOCUMENTED",
        "verification_state": item["verification_state"],
        "notes": "{} Supported claims: {}".format(item["notes"], "; ".join(item.get("supports", []))),
    }


def _pack(pack_id: str, kind: str, references: List[Dict[str, Any]], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    source_ids = sorted({item["source"] for item in references})
    owned_evidence = (
        [item for item in evidence if item["evidence_id"] != "EVID-P12-SLSA"]
        if pack_id == AGENT_PACK_ID
        else [item for item in evidence if item["evidence_id"] == "EVID-P12-SLSA"]
        if pack_id == SUPPLY_PACK_ID
        else []
    )
    return {
        "pack_id": pack_id,
        "pack_version": "1.0.0",
        "kind": kind,
        "display_name": {
            AGENT_PACK_ID: "Agentic AI Security Pack",
            SUPPLY_PACK_ID: "Software Supply Chain Security Pack",
            CROSS_PACK_ID: "Phase 12 Cross-Domain Correlation Pack",
        }[pack_id],
        "maturity": "BETA",
        "verification_state": "PARTIALLY_VERIFIED",
        "dependencies": [],
        "evidence": owned_evidence,
        "sources": [_source(source_id, references) for source_id in source_ids],
        "integrations": [],
        "generators": [_generator(source_id) for source_id in source_ids],
        "validators": [_validator(source_id) for source_id in source_ids],
        "transports": [],
        "destinations": [],
        "declarative_templates": [],
        "integration_recommendations": [_recommendation(source_id) for source_id in source_ids],
        "scenarios": [_manifest(item) for item in references],
        "investigations": [_investigation(item) for item in references],
        "industries": [],
    }


def _source(source_id: str, references: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    config = SOURCE_CONFIG[source_id]
    scenario_ids = [item["scenario_id"] for item in references if item["source"] == source_id]
    is_agentic = source_id == "phase12-agentic-audit"
    protocol_fields = (
        ["jsonrpc", "id", "method", "params", "result", "error", "uri"]
        if is_agentic
        else ["predicateType", "subject", "buildDefinition", "runDetails", "builder.id", "digest"]
    )
    return {
        "source": {
            "source_id": source_id,
            "vendor": "NetSpout",
            "product": config["product"],
            "product_family": config["family"],
            "domains": ["security", "agentic-ai" if is_agentic else "software-supply-chain"],
            "telemetry_source": "NetSpout-defined deterministic instrumentation audit events",
            "applicable_industries": [],
            "verification_state": "PARTIALLY_VERIFIED",
            "provenance": ["STANDARD_DOCUMENTED", "NETSPOUT_SCHEMA", "MODELED_VALUE"],
            "evidence_ids": config["evidence"],
            "native_contract": {
                "contract_id": f"native-{source_id}",
                "verification_state": "PARTIALLY_VERIFIED",
                "format": "NetSpout Phase 12 Audit Envelope JSON",
                "schema": "protocol, audit, scenario layers",
                "transports": [{"protocol": "HEC", "encoding": "UTF-8 JSON"}],
                "structural_fields": ["schema_version", "event_layer", "protocol", "audit", "scenario"] + protocol_fields,
                "evidence_ids": config["evidence"],
            },
            "splunk_contract": {
                "contract_id": f"splunk-{source_id}",
                "verification_state": "PARTIALLY_VERIFIED",
                "input_mechanisms": ["NetSpout local HEC dispatcher"],
                "integration_ids": [],
                "sourcetypes": [{"name": config["sourcetype"], "authority": "NETSPOUT_DEFINED", "evidence_ids": ["EVID-P12-RUNTIME"]}],
                "cim_mappings": [],
                "evidence_ids": ["EVID-P12-RUNTIME"],
            },
            "netspout_contract": {
                "contract_id": f"netspout-{source_id}",
                "verification_state": "PARTIALLY_VERIFIED",
                "schema_classification": "NETSPOUT_SCHEMA",
                "generator": config["generator"],
                "validator": config["validator"],
                "transports": ["transport-local-hec"],
                "modeled_fields": ["synthetic identities", "policy outcome", "timestamps", "content summaries"],
                "structural_fields": ["separate protocol, audit, and scenario namespaces", "causal_parent_id", "correlation_id"],
                "scenario_ids": scenario_ids,
                "generation_modes": ["SCENARIO", "DATA_SOURCE", "SINGLE_EVENT"],
                "runtime_status": "AVAILABLE",
                "maturity": "CONTRACT_VALIDATED",
                "evidence_ids": config["evidence"],
            },
            "spl_field_scope": {
                "production_fields": [],
                "netspout_only_fields": ["netspout_run_id", "netspout_scenario_id", "netspout_phase", "correlation_id", "causal_parent_id"],
                "portable_spl_status": "RESEARCH_REQUIRED",
            },
            "known_limitations": [
                "This is instrumentation-generated audit telemetry, not a native MCP/A2A/CI wire capture.",
                "Protocol-shaped fields are limited to the cited structures and do not imply runtime support.",
                "CIM compatibility is NOT_ESTABLISHED.",
                "Synthetic tests do not establish production detection efficacy.",
            ],
        },
        "generator_ids": [config["generator"]],
        "validator_ids": [config["validator"]],
        "compatible_transport_ids": ["transport-local-hec"],
        "raw_fidelity": {
            "preserve_native_raw": True,
            "modeled_values_may_change": True,
            "structural_mutation_allowed": False,
            "normalization_owner": "SPLUNK_INTEGRATION",
            "cim_validation_stage": "CIM_VERIFIED",
        },
        "sample_derived": False,
        "ai_assisted_analysis": False,
    }


def _generator(source_id: str) -> Dict[str, Any]:
    config = SOURCE_CONFIG[source_id]
    return {
        "generator_id": config["generator"],
        "implementation_ref": "netspout_core.phase12_security_packs.generate_phase12_event",
        "source_ids": [source_id],
        "signals": ["LOGS", "EVENTS"],
        "verification_state": "PARTIALLY_VERIFIED",
        "evidence_ids": config["evidence"],
    }


def _validator(source_id: str) -> Dict[str, Any]:
    config = SOURCE_CONFIG[source_id]
    return {
        "validator_id": config["validator"],
        "implementation_ref": "netspout_core.phase12_security_packs.validate_phase12_event",
        "source_ids": [source_id],
        "stages": ["RAW_VERIFIED", "SENT", "SPLUNK_OBSERVED", "FIELDS_VERIFIED"],
        "evidence_ids": config["evidence"],
    }


def _recommendation(source_id: str) -> Dict[str, Any]:
    return {
        "recommendation_id": f"recommend-{source_id}",
        "source_id": source_id,
        "integration_id": None,
        "requirement": "NOT_REQUIRED",
        "evidence_ids": ["EVID-P12-RUNTIME"],
        "notes": "The lab uses a NETSPOUT_DEFINED sourcetype; production integration and field mapping remain environment-specific.",
    }


def _investigation(reference: Mapping[str, Any]) -> Dict[str, Any]:
    source_id = reference["source"]
    sourcetype = SOURCE_CONFIG[source_id]["sourcetype"]
    return {
        "recipe_id": f"p12-investigate-{reference['scenario_id'].lower()}",
        "title": f"Investigate {reference['title']}",
        "objective": reference["threat"],
        "question": "What was requested, what did policy decide, and which downstream effects were actually observed?",
        "expected_finding": f"The modeled outcome is {reference['outcome']}; denied or rejected actions have no successful downstream action.",
        "explanation": "The search separates protocol-shaped data, instrumentation audit evidence, and NetSpout scenario metadata.",
        "hint": "Do not infer compromise or deployment from an attempt, denial, missing provenance, or protocol exchange alone.",
        "portability": "NETSPOUT_SPECIFIC",
        "spl": f'search index="idx_network_ops" sourcetype="{sourcetype}" netspout_run_id="$run_id$" earliest=-15m latest=now | sort 0 _time | table _time netspout_phase event_type action outcome correlation_id causal_parent_id protocol_family protocol_method',
        "source_ids": [source_id],
        "required_fields": ["netspout_run_id", "netspout_phase", "event_type", "outcome", "correlation_id", "causal_parent_id"],
        "cim_requirements": [],
        "netspout_only_fields": ["netspout_run_id", "netspout_phase", "correlation_id", "causal_parent_id"],
        "evidence_ids": ["EVID-P12-RUNTIME"],
    }


def _manifest(reference: Mapping[str, Any]) -> Dict[str, Any]:
    scenario_id = reference["scenario_id"]
    source_id = reference["source"]
    suffix = scenario_id.lower()
    incident_id = f"incident-{suffix}"
    nodes = [
        {"node_id": f"{suffix}-actor", "technology_id": "synthetic-identity", "zone_id": "control", "role": "agent-or-automation", "source_ids": [source_id], "label": "Synthetic Actor", "entity_id": f"{suffix}-actor"},
        {"node_id": f"{suffix}-resource", "technology_id": "synthetic-resource", "zone_id": "resource", "role": "tool-repository-or-runtime", "source_ids": [source_id], "label": "Synthetic Resource", "entity_id": f"{suffix}-resource"},
        {"node_id": f"{suffix}-policy", "technology_id": "policy-engine", "zone_id": "control", "role": "authorization-policy", "source_ids": [source_id], "label": "Policy Decision", "entity_id": f"{suffix}-policy"},
        {"node_id": f"{suffix}-splunk", "technology_id": "splunk-enterprise", "zone_id": "analytics", "role": "investigation", "source_ids": [], "label": "Local Splunk", "entity_id": f"{suffix}-splunk"},
    ]
    stages = (
        ("BASELINE", "Stable identities, authorization, and expected state are established.", []),
        ("PRECURSOR", "The bounded synthetic input or change reaches a trust boundary.", []),
        ("INCIDENT", reference["threat"], [incident_id]),
        ("DETECTION", "Policy and audit evidence are evaluated independently of intent.", [incident_id]),
        ("RECOVERY", "The scenario records its bounded final state and no external side effect.", []),
    )
    recipe_id = f"p12-investigate-{suffix}"
    evidence_ids = SOURCE_CONFIG[source_id]["evidence"]
    detection_id = f"P12-DET-{scenario_id}"
    fields = ["event_type", "action", "outcome", "correlation_id", "causal_parent_id"]
    return {
        "scenario_id": scenario_id,
        "title": reference["title"],
        "description": reference["threat"],
        "story": reference["simple"],
        "domain": reference["domain"],
        "category": reference["category"],
        "technical_description": reference["advanced"],
        "difficulty": "BEGINNER_TO_ADVANCED",
        "expected_duration_minutes": 15,
        "learning_objectives": [
            "Distinguish an attempted, allowed, denied, blocked, modeled, and observed action.",
            "Separate protocol-defined structures from instrumentation and scenario metadata.",
            "Adapt a run-scoped investigation without claiming synthetic efficacy.",
        ],
        "skills_practiced": ["Trust-boundary analysis", "Causal correlation", "Splunk investigation"],
        "expected_outcome": reference["outcome"],
        "baseline_description": "Synthetic stable identities and least-privilege policy establish the comparison state.",
        "incident_description": reference["threat"],
        "discovery_prompt": "Which boundary was crossed, what evidence exists, and what remains unproven?",
        "learning_hints": [reference["simple"], reference["advanced"]],
        "business_impact": "Defenders can investigate risky automation without overstating compromise, deployment, or malicious intent.",
        "prerequisites": ["Local deterministic runtime", "Configured local Splunk destination for live observation"],
        "technology_ids": ["phase12-audit-contract", reference["protocol"].lower(), "splunk-enterprise"],
        "source_ids": [source_id],
        "entities": [item["entity_id"] for item in nodes],
        "zones": [{"zone_id": "control", "label": "Control Plane"}, {"zone_id": "resource", "label": "Resource Plane"}, {"zone_id": "analytics", "label": "Analytics"}],
        "nodes": nodes,
        "relationships": [
            {"relationship_id": f"{suffix}-request", "source_node_id": f"{suffix}-actor", "target_node_id": f"{suffix}-resource", "relationship_type": "requests", "protocol": reference["protocol"], "purpose": "Bounded synthetic request.", "telemetry_source_ids": [source_id], "incident_relevance": reference["boundary"]},
            {"relationship_id": f"{suffix}-decision", "source_node_id": f"{suffix}-policy", "target_node_id": f"{suffix}-actor", "relationship_type": "evaluates", "purpose": "Externalized policy decision.", "telemetry_source_ids": [source_id], "incident_relevance": "Policy outcome is evidence; model intent is not authorization."},
            {"relationship_id": f"{suffix}-observe", "source_node_id": f"{suffix}-actor", "target_node_id": f"{suffix}-splunk", "relationship_type": "evidence-path", "protocol": "HEC", "purpose": "Run-scoped audit observation.", "telemetry_source_ids": [source_id], "incident_relevance": "HEC acceptance and indexed observation remain separate."},
        ],
        "telemetry_paths": [{"path_id": f"{suffix}-audit-path", "source_id": source_id, "producer_node_id": f"{suffix}-actor", "observer_node_id": f"{suffix}-splunk", "label": "Instrumentation audit path", "protocol": "JSON over local HEC"}],
        "incident_path": [f"{suffix}-actor", f"{suffix}-policy", f"{suffix}-resource", f"{suffix}-splunk"],
        "incident_summary": reference["threat"],
        "runtime_state_keys": ["phase12.identity", "phase12.authorization", "phase12.outcome", "phase12.causal_parent"],
        "timeline": [
            {
                "step_id": f"{suffix}-{stage.lower()}",
                "stage": stage,
                "description": description,
                "state_changes": {"phase12.outcome": reference["outcome"] if stage in {"INCIDENT", "DETECTION"} else stage},
                "entity_state_changes": {f"{suffix}-actor": stage},
                "telemetry_state_changes": {source_id: "EXPECTED"},
                "expected_observations": ["One deterministic event shares the run correlation graph and preserves outcome semantics."],
                "evidence_source_ids": [source_id],
                "incident_ids": incident_ids,
            }
            for stage, description, incident_ids in stages
        ],
        "incidents": [{"incident_id": incident_id, "source_ids": [source_id], "assertion": reference["threat"], "corroboration_required": False}],
        "parameters": [
            {"parameter_id": "intensity", "value_type": "integer", "changes_modeled_values_only": True},
            {"parameter_id": "policy_mode", "value_type": "enum", "changes_modeled_values_only": True},
        ],
        "integration_recommendation_ids": [f"recommend-{source_id}"],
        "expected_evidence": ["GENERATED", "RAW_VERIFIED", "SENT", "SPLUNK_OBSERVED", "FIELDS_VERIFIED"],
        "investigation_recipe_ids": [recipe_id],
        "investigation_steps": [
            {
                "step_id": f"{suffix}-guided-{index}",
                "recipe_id": recipe_id,
                "title": title,
                "question": question,
                "expected_finding": finding,
                "explanation": explanation,
                "hint": "Keep modeled causality, observed evidence, and analyst inference separate.",
                "node_ids": [f"{suffix}-actor", f"{suffix}-splunk"],
                "source_ids": [source_id],
            }
            for index, (title, question, finding, explanation) in enumerate(
                [
                    ("Understand the threat", "What is the threat?", reference["threat"], reference["simple"]),
                    ("Inspect the boundary", "Which trust boundary is crossed?", reference["boundary"], reference["advanced"]),
                    ("Compare evidence", "What evidence should and does exist?", "Run, identity, request, policy, outcome, and causal identifiers are available.", "Availability depends on explicit instrumentation."),
                    ("Investigate in Splunk", "How does Splunk help?", "A fresh run-scoped search orders the audit timeline.", "Splunk observes records; it does not independently prove intent."),
                    ("Bound the claim", "What does the detection prove and not prove?", f"It matches the modeled {reference['outcome']} outcome; it does not prove real-world compromise.", "Synthetic validation is not production efficacy."),
                    ("Apply controls", "Which controls reduce risk?", "Least privilege, external authorization, provenance checks, bounded tools, and audit logging.", "Map fields and authorization sources to the real environment."),
                ],
                start=1,
            )
        ],
        "validation_expectations": [
            {"validation_id": f"{suffix}-splunk-observed", "label": "Fresh authenticated Splunk observation", "evidence_stage": "SPLUNK_OBSERVED", "expected_state": "PROVEN", "requirement": "REQUIRED", "source_id": source_id},
            {"validation_id": f"{suffix}-fields-verified", "label": "Required audit and correlation fields", "evidence_stage": "FIELDS_VERIFIED", "expected_state": "PROVEN", "requirement": "REQUIRED", "source_id": source_id},
        ],
        "visualization": {"mode": "AUTOMATIC", "direction": "LEFT_TO_RIGHT"},
        "replay_policy": {"creates_new_run_id": True, "preserves_history": True, "reset_to_step": "RUN"},
        "troubleshooting_steps": ["Verify HEC acknowledgement before fresh Splunk search.", "Inspect protocol, audit, and scenario namespaces independently."],
        "cim_validation": ["NOT_ESTABLISHED for Phase 12 NetSpout-defined audit sourcetypes."],
        "production_replication_guidance": ["Replace NetSpout-only correlation with stable production session, task, build, artifact, policy, and identity fields.", "Revalidate field names, authorization semantics, and time windows against the deployed implementation."],
        "security_behavior_stages": ["BASELINE", "ATTEMPT", reference["outcome"], "DETECTION", "RECOVERY"],
        "kpi_definitions": [{"kpi_id": f"{suffix}-outcomes", "label": "Observed outcomes", "analytic_id": "phase12-outcome-count", "required_source_ids": [source_id], "required_fields": fields, "interpretation_limit": "Counts describe synthetic audit outcomes, not compromise prevalence."}],
        "detection_validation": [{
            "detection_id": detection_id,
            "objective": f"Identify the bounded {reference['title']} evidence pattern.",
            "threat_behavior": reference["threat"],
            "mitre_attack_ids": [],
            "required_source_ids": [source_id],
            "required_fields": fields,
            "spl": f'search index="idx_network_ops" sourcetype="{SOURCE_CONFIG[source_id]["sourcetype"]}" netspout_run_id="$run_id$" earliest=-15m latest=now | spath | search outcome="{reference["outcome"]}" | stats count values(outcome) as outcomes by correlation_id',
            "portability": "NETSPOUT_SPECIFIC",
            "baseline_expected_result": "Baseline does not contain the incident outcome.",
            "incident_expected_result": f"Incident records contain {reference['outcome']} with one shared correlation identifier.",
            "false_positive_controls": ["Scope to one run and verify policy outcome before escalation.", "Treat missing provenance and protocol exchange as risk signals, not malicious verdicts."],
            "blind_spots": ["Synthetic identities and content do not establish production behavior.", "No external model, MCP/A2A peer, CI, repository, registry, or deployment was contacted."],
            "validation_outcome": "SPLUNK_VALIDATED",
            "evidence_ids": evidence_ids,
        }],
        "false_positive_controls": ["Confirm the authorization decision and downstream action separately.", "Require independent evidence before asserting impact."],
        "known_blind_spots": ["No production CIM mapping is established.", "No external system behavior is validated by this offline simulation."],
        "expected_findings": [reference["outcome"], "Stable run and causal identifiers", "No secret material or external execution"],
        "scenario_maturity": "SPLUNK_VALIDATED",
    }


def _composition(pack_id: str, reference: Mapping[str, Any]) -> Dict[str, Any]:
    source_id = reference["source"]
    config = SOURCE_CONFIG[source_id]
    scenario_id = reference["scenario_id"]
    return {
        "composition_id": f"composition-{scenario_id.lower()}",
        "scenario_id": scenario_id,
        "pack_ids": [pack_id],
        "source_bindings": [{
            "source_id": source_id,
            "generator_id": config["generator"],
            "transport_id": "transport-local-hec",
            "destination_id": "destination-local-docker-splunk",
            "validator_ids": [config["validator"]],
        }],
        "investigation_recipe_ids": [f"p12-investigate-{scenario_id.lower()}"],
        "execution_mode": "SINGLE_EVENT",
        "correlate_native_channels": False,
    }


def _protocol_view(scenario_id: str, phase: str, ordinal: int) -> Dict[str, Any]:
    if scenario_id == "AI-005" or (
        scenario_id == "AI-006"
        and phase in {"INCIDENT", "DETECTION", "RECOVERY"}
    ):
        return {
            "family": "A2A",
            "version": "1.0.0",
            "taskId": f"task-{scenario_id.lower()}",
            "contextId": f"context-{scenario_id.lower()}",
            "message": {"role": "ROLE_AGENT", "parts": [{"text": "bounded synthetic task"}]},
            "status": {"state": "TASK_STATE_REJECTED" if phase == "INCIDENT" else "TASK_STATE_WORKING"},
        }
    if scenario_id.startswith("AI-") or scenario_id == "P12-XD-001":
        method = "tools/call" if phase in {"INCIDENT", "DETECTION"} else "tools/list"
        return {
            "family": "MCP",
            "version": "2025-11-25",
            "jsonrpc": "2.0",
            "id": ordinal + 1,
            "method": method,
            "params": {"name": "synthetic.read_only_tool", "arguments": {"artifact_ref": "fixture://benign"}},
        }
    return {
        "family": "SLSA",
        "version": "1.1",
        "predicateType": "https://slsa.dev/provenance/v1",
        "subject": [{"name": "registry.invalid/netspout/test-artifact", "digest": {"sha256": hashlib.sha256(scenario_id.encode()).hexdigest()}}],
        "buildDefinition": {"buildType": "https://netspout.invalid/build/v1", "externalParameters": {"synthetic": True}},
        "runDetails": {"builder": {"id": "https://netspout.invalid/builders/offline"}},
    }


def _outcome_for(scenario_id: str, phase: str) -> str:
    if phase not in {"INCIDENT", "DETECTION"}:
        return "NO_ACTION" if phase == "BASELINE" else phase
    outcomes = {
        "AI-001": "BLOCKED", "AI-002": "DENIED", "AI-003": "CONTAINED",
        "AI-004": "DENIED", "AI-005": "REJECTED", "AI-006": "DENIED",
        "SC-001": "REVIEW_REQUIRED", "SC-002": "DENIED", "SC-003": "VALIDATION_FAILED",
        "SC-004": "DENIED", "SC-005": "MODELED_DEPLOYMENT",
        "P12-XD-001": "DENIED", "P12-XD-002": "MODELED_DEPLOYMENT",
    }
    return outcomes.get(scenario_id, "MODELED")


def generate_phase12_event(
    *,
    run_id: str,
    phase: str,
    ordinal: int,
    event_family: str,
    scenario_parameters: Mapping[str, Any],
) -> Phase12GeneratedEvent:
    """Generate one bounded, redacted, deterministic audit event."""

    del event_family
    scenario_id = str(scenario_parameters.get("_scenario_id") or "AI-001")
    behavior_scenario_id = str(
        scenario_parameters.get("reference_scenario_id") or scenario_id
    )
    source_id = str(scenario_parameters.get("_source_id") or (
        "phase12-agentic-audit" if scenario_id.startswith("AI-") else
        "phase12-cross-domain-audit" if scenario_id.startswith("P12-XD-") else
        "phase12-supply-chain-audit"
    ))
    config = SOURCE_CONFIG.get(source_id)
    if config is None:
        raise ValueError("Phase 12 source is not allow-listed")
    supplied = {key: value for key, value in scenario_parameters.items() if not key.startswith("_")}
    unknown = sorted(set(supplied) - _ALLOWED_PARAMETERS)
    if unknown:
        raise ValueError("unsupported scenario parameters: {}".format(", ".join(unknown)))
    _reject_unsafe_values(supplied)
    seed = int(scenario_parameters.get("_seed", 1200))
    plan = build_phase12_state_plan(run_id, scenario_id, seed)
    outcome = _outcome_for(behavior_scenario_id, phase)
    actor = plan.entities[0]["entity_id"]
    resource = plan.entities[1]["entity_id"]
    event_id = f"{plan.correlation_id}-{ordinal:02d}"
    raw = {
        "schema_version": "1.0.0",
        "event_layer": "INSTRUMENTATION_AUDIT",
        "protocol": _protocol_view(behavior_scenario_id, phase, ordinal),
        "audit": {
            "event_type": "policy_evaluation" if phase in {"INCIDENT", "DETECTION"} else "lifecycle",
            "actor_id": actor,
            "resource_id": resource,
            "action": "synthetic.request",
            "outcome": outcome,
            "authorization_source": plan.entities[2]["entity_id"],
            "credential_reference": "synthetic-ref-redacted",
            "downstream_action_executed": outcome == "MODELED_DEPLOYMENT",
            "content_trust": "LOWER_TRUST" if phase in {"PRECURSOR", "INCIDENT"} else "CONTROLLED",
        },
        "scenario": {
            "netspout_run_id": run_id,
            "netspout_scenario_id": scenario_id,
            "reference_scenario_id": behavior_scenario_id,
            "netspout_phase": phase,
            "correlation_id": plan.correlation_id,
            "causal_parent_id": None if ordinal == 0 else f"{plan.correlation_id}-{ordinal - 1:02d}",
            "event_id": event_id,
            "timestamp_ns": plan.timestamp_ns(phase),
            "evidence_classification": "MODELED" if outcome == "MODELED_DEPLOYMENT" else "OBSERVED_INSTRUMENTATION",
        },
    }
    flattened = {
        **raw,
        "event_type": raw["audit"]["event_type"],
        "action": raw["audit"]["action"],
        "outcome": outcome,
        "correlation_id": plan.correlation_id,
        "causal_parent_id": raw["scenario"]["causal_parent_id"] or "",
        "protocol_family": raw["protocol"]["family"],
        "protocol_method": raw["protocol"].get("method", ""),
        "netspout_run_id": run_id,
        "netspout_scenario_id": scenario_id,
        "netspout_phase": phase,
    }
    encoded = json.dumps(flattened, sort_keys=True, separators=(",", ":"))
    return Phase12GeneratedEvent(
        event_id=event_id,
        source_id=source_id,
        contract_id=f"netspout-{source_id}",
        provenance=["STANDARD_DOCUMENTED", "NETSPOUT_SCHEMA", "MODELED_VALUE"],
        transport_id="transport-local-hec",
        sourcetype=config["sourcetype"],
        sourcetype_authority="NETSPOUT_DEFINED",
        phase=phase,
        raw=encoded,
    )


def _reject_unsafe_values(value: Any, path: str = "parameters") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _SECRET_KEYS.search(str(key)):
                raise ValueError(f"{path}.{key} may contain credential material")
            _reject_unsafe_values(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_unsafe_values(item, f"{path}[{index}]")
    elif isinstance(value, str):
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https", "ssh", "git"}:
            raise ValueError("external endpoints and repositories are not allowed")
        if any(token in value for token in ("$(", "`", "&&", "||", "\n#!")):
            raise ValueError("executable payload syntax is not allowed")


def validate_phase12_event(raw: str) -> bool:
    """Validate layer separation, correlation, outcomes, and secret absence."""

    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    required = {"protocol", "audit", "scenario", "event_type", "outcome", "correlation_id", "netspout_run_id", "netspout_scenario_id", "netspout_phase"}
    if not required.issubset(payload):
        return False
    if payload.get("event_layer") != "INSTRUMENTATION_AUDIT":
        return False
    if not all(isinstance(payload.get(key), dict) for key in ("protocol", "audit", "scenario")):
        return False
    if payload["audit"].get("outcome") in {"DENIED", "BLOCKED", "REJECTED", "VALIDATION_FAILED"} and payload["audit"].get("downstream_action_executed"):
        return False
    try:
        _reject_unsafe_values(payload["audit"])
        _reject_unsafe_values(payload["scenario"])
    except ValueError:
        return False
    return True


def phase12_generator_adapters() -> Dict[str, Any]:
    return {config["generator"]: generate_phase12_event for config in SOURCE_CONFIG.values()}


def phase12_validator_adapters() -> Dict[str, Any]:
    return {config["validator"]: validate_phase12_event for config in SOURCE_CONFIG.values()}


__all__ = [
    "Phase12StatePlan",
    "build_phase12_state_plan",
    "extend_registry",
    "generate_phase12_event",
    "phase12_generator_adapters",
    "phase12_validator_adapters",
    "validate_phase12_event",
]
