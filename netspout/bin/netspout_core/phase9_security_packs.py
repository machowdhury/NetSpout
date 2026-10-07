"""Compile compact Phase 9 security references into strict pack contracts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


PACK_ID = "netspout-phase9-network-security"
DNS_SOURCE_ID = "ietf-dns-rfc1035"
DNS_GENERATOR_ID = "generator-native-dns-rfc1035"
DNS_VALIDATOR_ID = "validator-native-dns-boundary"
DNS_TRANSPORT_ID = "transport-native-dns-udp"
HEC_TRANSPORT_ID = "transport-local-hec"
DESTINATION_ID = "destination-local-docker-splunk"
RUNTIME_EVIDENCE_ID = "EVID-P9-NETSPOUT-RUNTIME"


def extend_registry(
    base_registry: Dict[str, Any], specification: Dict[str, Any]
) -> Dict[str, Any]:
    registry = deepcopy(base_registry)
    registry["registry_version"] = specification["registry_version"]
    pack = _build_pack(specification)
    registry["packs"].append(pack)
    registry["compositions"].extend(
        _composition(reference) for reference in specification["references"]
    )
    return registry


def _build_pack(specification: Dict[str, Any]) -> Dict[str, Any]:
    references = specification["references"]
    investigations = [
        recipe
        for reference in references
        for recipe in _investigations(reference)
    ]
    return {
        "pack_id": PACK_ID,
        "pack_version": "0.9.0",
        "kind": "SCENARIO",
        "display_name": "Network Security Analytics and SecOps Lab",
        "maturity": "BETA",
        "verification_state": "PARTIALLY_VERIFIED",
        "dependencies": [],
        "evidence": specification["evidence"],
        "sources": [_dns_source()],
        "integrations": [],
        "generators": [
            {
                "generator_id": DNS_GENERATOR_ID,
                "implementation_ref": (
                    "netspout_core.native_runtime.NativeRuntimeFacade.run_dns"
                ),
                "source_ids": [DNS_SOURCE_ID],
                "signals": ["PACKETS", "EVENTS"],
                "verification_state": "PARTIALLY_VERIFIED",
                "evidence_ids": ["EVID-P9-IETF-RFC1035", RUNTIME_EVIDENCE_ID],
            }
        ],
        "validators": [
            {
                "validator_id": DNS_VALIDATOR_ID,
                "implementation_ref": "netspout_core.dns_wire.parse_message",
                "source_ids": [DNS_SOURCE_ID],
                "stages": [
                    "RAW_VERIFIED",
                    "SENT",
                    "RECEIVER_OBSERVED",
                    "SPLUNK_OBSERVED",
                ],
                "evidence_ids": ["EVID-P9-IETF-RFC1035", RUNTIME_EVIDENCE_ID],
            }
        ],
        "transports": [
            {
                "transport_id": DNS_TRANSPORT_ID,
                "component": "Bundled RFC 1035 DNS loopback observer",
                "protocol": "DNS over UDP",
                "signals": ["PACKETS", "EVENTS"],
                "compatible_source_ids": [DNS_SOURCE_ID],
                "verification_state": "PARTIALLY_VERIFIED",
                "implemented": True,
                "evidence_ids": ["EVID-P9-IETF-RFC1035", RUNTIME_EVIDENCE_ID],
                "notes": (
                    "Native DNS terminates at a bundled loopback receiver. "
                    "Normalization and HEC delivery are separate evidence stages."
                ),
            }
        ],
        "destinations": [],
        "declarative_templates": [],
        "integration_recommendations": [
            {
                "recommendation_id": "recommend-phase9-dns-lab-ingestion",
                "source_id": DNS_SOURCE_ID,
                "integration_id": None,
                "requirement": "NOT_REQUIRED",
                "evidence_ids": [RUNTIME_EVIDENCE_ID],
                "notes": (
                    "The normalized sourcetype is NETSPOUT_DEFINED. Resolver, "
                    "authoritative-server, and security-product integrations "
                    "remain distinct production choices."
                ),
            }
        ],
        "scenarios": [_manifest(reference) for reference in references],
        "investigations": investigations,
        "industries": [],
    }


def _dns_source() -> Dict[str, Any]:
    return {
        "source": {
            "source_id": DNS_SOURCE_ID,
            "vendor": "IETF",
            "product": "Domain Name System",
            "product_family": "DNS Protocol",
            "domains": ["secops", "network"],
            "telemetry_source": "Observed RFC 1035 DNS query and response exchange",
            "applicable_industries": [],
            "verification_state": "PARTIALLY_VERIFIED",
            "provenance": [
                "STANDARD_DOCUMENTED",
                "NETSPOUT_SCHEMA",
                "MODELED_VALUE",
            ],
            "evidence_ids": ["EVID-P9-IETF-RFC1035", RUNTIME_EVIDENCE_ID],
            "native_contract": {
                "contract_id": "native-ietf-dns-rfc1035",
                "verification_state": "VERIFIED",
                "format": "RFC 1035 DNS query and response message",
                "schema": "RFC 1035 sections 4.1 and 4.1.1",
                "transports": [
                    {
                        "protocol": "UDP",
                        "default_port": 53,
                        "encoding": "Binary network byte order",
                    }
                ],
                "structural_fields": [
                    "transaction ID",
                    "flags",
                    "question count",
                    "answer count",
                    "QNAME",
                    "QTYPE",
                    "QCLASS",
                    "RCODE",
                ],
                "evidence_ids": ["EVID-P9-IETF-RFC1035"],
            },
            "splunk_contract": {
                "contract_id": "splunk-ietf-dns-rfc1035",
                "verification_state": "PARTIALLY_VERIFIED",
                "input_mechanisms": [
                    "Bundled native DNS observer followed by separate HEC delivery"
                ],
                "integration_ids": [],
                "sourcetypes": [
                    {
                        "name": "netspout:dns:wire",
                        "authority": "NETSPOUT_DEFINED",
                        "evidence_ids": [RUNTIME_EVIDENCE_ID],
                    }
                ],
                "cim_mappings": [],
                "evidence_ids": [RUNTIME_EVIDENCE_ID],
            },
            "netspout_contract": {
                "contract_id": "netspout-ietf-dns-rfc1035",
                "verification_state": "PARTIALLY_VERIFIED",
                "schema_classification": "MODELED_VALUE",
                "generator": DNS_GENERATOR_ID,
                "validator": DNS_VALIDATOR_ID,
                "transports": [DNS_TRANSPORT_ID],
                "modeled_fields": [
                    "query name",
                    "query type",
                    "response code",
                    "answer address",
                    "timing",
                ],
                "structural_fields": [
                    "RFC 1035 header",
                    "question",
                    "answer resource record",
                    "network byte order",
                ],
                "scenario_ids": [],
                "generation_modes": ["SCENARIO", "DATA_SOURCE"],
                "runtime_status": "AVAILABLE",
                "maturity": "SPLUNK_VALIDATED",
                "evidence_ids": ["EVID-P9-IETF-RFC1035", RUNTIME_EVIDENCE_ID],
            },
            "spl_field_scope": {
                "production_fields": [
                    "query",
                    "query_type",
                    "response_code",
                    "answer",
                    "client_ip",
                    "resolver_ip",
                ],
                "netspout_only_fields": [
                    "attack_related",
                    "netspout_run_id",
                    "netspout_scenario_id",
                    "netspout_phase",
                ],
                "portable_spl_status": "RESEARCH_REQUIRED",
            },
            "known_limitations": [
                "This is a native DNS protocol observation, not a universal resolver log.",
                "The normalized sourcetype is NETSPOUT_DEFINED.",
                "EDNS, DNSSEC, TCP fallback, IPv6 answers, and name-server recursion are not modeled.",
                "CIM mapping is NOT_ESTABLISHED.",
            ],
        },
        "generator_ids": [DNS_GENERATOR_ID],
        "validator_ids": [DNS_VALIDATOR_ID],
        "compatible_transport_ids": [DNS_TRANSPORT_ID],
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


def _source_label(source_id: str) -> str:
    return "DNS" if source_id == DNS_SOURCE_ID else "IPFIX"


def _source_sourcetype(source_id: str) -> str:
    return "netspout:dns:wire" if source_id == DNS_SOURCE_ID else "netflow:collector"


def _investigations(reference: Dict[str, Any]) -> List[Dict[str, Any]]:
    scenario_id = reference["scenario_id"]
    suffix = scenario_id.lower()
    source_scope = " OR ".join(
        'sourcetype="{}"'.format(_source_sourcetype(source_id))
        for source_id in reference["sources"]
    )
    base = (
        'search index="idx_network_ops" ({}) netspout_run_id="$run_id$"'
    ).format(source_scope)
    evidence_ids = _reference_evidence(reference)
    common = {
        "source_ids": reference["sources"],
        "cim_requirements": [],
        "netspout_only_fields": ["netspout_run_id"],
        "evidence_ids": evidence_ids,
        "portability": "NETSPOUT_SPECIFIC",
    }
    analytic_spl = _analytic_spl(reference["sources"])
    recipes = [
        {
            "recipe_id": "p9-find-incident-" + suffix,
            "title": "Find the bounded incident",
            "objective": "Confirm records for the selected run without cross-run contamination.",
            "question": "Which source families observed this run?",
            "expected_finding": "Only the scenario's declared source families appear.",
            "explanation": "The run identifier is NetSpout-only lab correlation metadata.",
            "hint": "Start with counts by sourcetype.",
            "spl": base + " | stats count by sourcetype",
            "required_fields": ["sourcetype", "netspout_run_id"],
        },
        {
            "recipe_id": "p9-timeline-" + suffix,
            "title": "Build the evidence timeline",
            "objective": "Order source observations and behavior stages.",
            "question": "Did baseline evidence precede the suspicious observations?",
            "expected_finding": "Baseline and incident records share the run but preserve source identity.",
            "explanation": "Temporal order supports correlation but does not prove causality.",
            "hint": "Inspect phase and source together.",
            "spl": base + " | sort 0 _time | table _time sourcetype netspout_phase host",
            "required_fields": ["_time", "sourcetype", "netspout_phase"],
        },
        {
            "recipe_id": "p9-analytics-" + suffix,
            "title": "Compare baseline with incident indicators",
            "objective": reference["objective"],
            "question": "How did source counts and entity diversity change?",
            "expected_finding": "The modeled incident differs from its own baseline.",
            "explanation": reference["blind_spot"],
            "hint": "Do not convert an anomaly into a compromise verdict.",
            "spl": base + analytic_spl,
            "required_fields": _recipe_fields(reference["sources"]),
        },
        {
            "recipe_id": "p9-detection-" + suffix,
            "title": "Evaluate the detection objective",
            "objective": reference["objective"],
            "question": "Does the bounded detection condition separate baseline from incident?",
            "expected_finding": "Incident observations meet the modeled condition; baseline does not.",
            "explanation": reference["false_positive"],
            "hint": "Apply the stated false-positive control before escalation.",
            "spl": base + analytic_spl,
            "required_fields": _recipe_fields(reference["sources"]),
        },
        {
            "recipe_id": "p9-validate-" + suffix,
            "title": "Validate expected and missing evidence",
            "objective": "Separate observed evidence from declared blind spots.",
            "question": "Which required sources were indexed and what remains unobservable?",
            "expected_finding": "Every declared source is counted independently; documented blind spots remain.",
            "explanation": reference["blind_spot"],
            "hint": "HEC acknowledgement is not indexed observation.",
            "spl": base + " | stats count dc(host) as entities by sourcetype",
            "required_fields": ["sourcetype", "host"],
        },
    ]
    return [{**common, **recipe} for recipe in recipes]


def _manifest(reference: Dict[str, Any]) -> Dict[str, Any]:
    scenario_id = reference["scenario_id"]
    suffix = scenario_id.lower()
    source_ids = reference["sources"]
    producer_sources = list(source_ids)
    nodes = [
        {
            "node_id": "p9-endpoint",
            "technology_id": "synthetic-endpoint",
            "zone_id": "user-zone",
            "role": "affected-host",
            "source_ids": producer_sources,
            "label": "TEST Endpoint",
            "entity_id": "test-endpoint-01",
            "description": "Fictional endpoint using RFC 5737 addresses.",
        },
        {
            "node_id": "p9-dns-resolver",
            "technology_id": "dns-rfc1035",
            "zone_id": "service-zone",
            "role": "dns-resolver",
            "source_ids": [item for item in source_ids if item == DNS_SOURCE_ID],
            "label": "TEST DNS Resolver",
            "entity_id": "test-resolver-01",
        },
        {
            "node_id": "p9-external",
            "technology_id": "reserved-destination",
            "zone_id": "external-zone",
            "role": "external-destination",
            "source_ids": [],
            "label": "Reserved External Destination",
            "entity_id": "test-external-01",
        },
        {
            "node_id": "p9-splunk",
            "technology_id": "splunk-enterprise",
            "zone_id": "analytics-zone",
            "role": "analytics",
            "source_ids": [],
            "label": "Local Splunk",
            "entity_id": "test-splunk.invalid",
        },
    ]
    relationships = [
        {
            "relationship_id": "p9-endpoint-dns-" + suffix,
            "source_node_id": "p9-endpoint",
            "target_node_id": "p9-dns-resolver",
            "relationship_type": "name-resolution",
            "protocol": "DNS/UDP",
            "purpose": "Observe modeled query and response behavior.",
            "telemetry_source_ids": [
                item for item in source_ids if item == DNS_SOURCE_ID
            ],
            "incident_relevance": "DNS evidence, when present, is one incident observation.",
        },
        {
            "relationship_id": "p9-endpoint-external-" + suffix,
            "source_node_id": "p9-endpoint",
            "target_node_id": "p9-external",
            "relationship_type": "network-communication",
            "protocol": "IP",
            "purpose": "Export bounded network-flow observations.",
            "telemetry_source_ids": [
                item for item in source_ids if item != DNS_SOURCE_ID
            ],
            "incident_relevance": "Flow evidence describes communication, not payload intent.",
        },
        {
            "relationship_id": "p9-evidence-splunk-" + suffix,
            "source_node_id": "p9-endpoint",
            "target_node_id": "p9-splunk",
            "relationship_type": "evidence-path",
            "protocol": "native receiver then HEC",
            "purpose": "Keep native receipt distinct from destination indexing.",
            "telemetry_source_ids": source_ids,
            "incident_relevance": "Supports independent per-source observation.",
        },
    ]
    telemetry_paths = [
        {
            "path_id": "p9-path-{}-{}".format(suffix, index),
            "source_id": source_id,
            "producer_node_id": (
                "p9-dns-resolver" if source_id == DNS_SOURCE_ID else "p9-endpoint"
            ),
            "observer_node_id": "p9-splunk",
            "label": _source_label(source_id) + " evidence path",
            "protocol": (
                "DNS/UDP then HEC"
                if source_id == DNS_SOURCE_ID
                else "IPFIX/UDP via bundled collector"
            ),
        }
        for index, source_id in enumerate(source_ids)
    ]
    stage_details = [
        ("BASELINE", "Normal comparison activity is emitted.", []),
        ("PRECURSOR", "The behavior begins to deviate from baseline.", []),
        ("INCIDENT", "Suspicious indicators become observable.", ["p9-incident-" + suffix]),
        ("IMPACT", "Potential defensive impact is evaluated without assuming compromise.", ["p9-incident-" + suffix]),
        ("DETECTION", "The bounded detection objective is evaluated.", ["p9-incident-" + suffix]),
        ("RECOVERY", "The scenario returns to its bounded end state.", []),
    ]
    timeline = [
        {
            "step_id": "{}-{}".format(suffix, stage.lower()),
            "stage": stage,
            "description": description,
            "state_changes": {"security.behavior": stage},
            "entity_state_changes": {"p9-endpoint": stage},
            "telemetry_state_changes": {
                source_id: "EXPECTED" for source_id in source_ids
            },
            "expected_observations": [
                "Each source retains independent evidence and limitations."
            ],
            "evidence_source_ids": source_ids,
            "incident_ids": incident_ids,
        }
        for stage, description, incident_ids in stage_details
    ]
    recipe_ids = [
        "p9-{}-{}".format(kind, suffix)
        for kind in ("find-incident", "timeline", "analytics", "detection", "validate")
    ]
    guided_titles = [
        "Find the incident",
        "Identify affected entities",
        "Build the timeline",
        "Inspect network flows",
        "Inspect DNS evidence",
        "Inspect corroborating observations",
        "Compare with baseline",
        "Evaluate detection results",
        "Identify blind spots",
        "Validate expected findings",
    ]
    guided_recipe_indexes = (0, 0, 1, 2, 2, 1, 2, 3, 4, 4)
    kpis = [
        {
            "kpi_id": "{}-{}".format(suffix, analytic),
            "label": analytic.replace("-", " ").title(),
            "analytic_id": analytic,
            "required_source_ids": (
                [DNS_SOURCE_ID]
                if analytic.startswith("dns-") or analytic == "domain-diversity"
                else source_ids
                if analytic == "cross-source-temporal-correlation"
                else ["ietf-ipfix"]
            ),
            "required_fields": _analytic_fields(analytic),
            "interpretation_limit": (
                "This metric describes a modeled deviation; it is not a malicious verdict."
            ),
        }
        for analytic in reference["analytics"]
    ]
    detection_spl = (
        'search index="idx_network_ops" netspout_run_id="$run_id$"'
        + _analytic_spl(source_ids)
    )
    return {
        "scenario_id": scenario_id,
        "title": reference["title"],
        "description": reference["objective"],
        "story": (
            "A controlled fictional enterprise exhibits {}. All observations "
            "derive from one seeded incident plan.".format(reference["family"].lower().replace("_", " "))
        ),
        "domain": "Security & SecOps",
        "category": reference["family"],
        "technical_description": (
            "The behavior model produces bounded RFC 1035 and/or IPFIX observations. "
            "Anomaly evidence is not represented as proof of compromise."
        ),
        "difficulty": "INTERMEDIATE",
        "expected_duration_minutes": 12,
        "learning_objectives": [
            "Separate behavior, native telemetry, Splunk observation, and detection validation.",
            "Apply baseline, false-positive, and blind-spot reasoning.",
        ],
        "skills_practiced": [
            "Network-flow analytics",
            "DNS analytics",
            "Cross-source investigation",
        ],
        "expected_outcome": reference["objective"],
        "baseline_description": "Bounded normal DNS and HTTPS activity establishes comparison evidence.",
        "incident_description": reference["objective"],
        "discovery_prompt": "What changed, which sources corroborate it, and what remains unproven?",
        "learning_hints": [
            reference["false_positive"],
            reference["blind_spot"],
        ],
        "business_impact": "A defender must triage suspicious network behavior without overstating evidence.",
        "prerequisites": [
            "Bundled native receivers",
            "Configured local Splunk destination",
            "Authenticated Splunk search for observation claims",
        ],
        "technology_ids": ["dns-rfc1035", "ipfix", "splunk-enterprise"],
        "source_ids": source_ids,
        "entities": [item["entity_id"] for item in nodes],
        "zones": [
            {"zone_id": "user-zone", "label": "User"},
            {"zone_id": "service-zone", "label": "Services"},
            {"zone_id": "external-zone", "label": "External"},
            {"zone_id": "analytics-zone", "label": "Analytics"},
        ],
        "nodes": nodes,
        "relationships": relationships,
        "telemetry_paths": telemetry_paths,
        "incident_path": ["p9-endpoint", "p9-dns-resolver", "p9-external", "p9-splunk"],
        "incident_summary": reference["objective"],
        "runtime_state_keys": [
            "security.behavior",
            "dns.query_rate",
            "flow.connection_rate",
        ],
        "timeline": timeline,
        "incidents": [
            {
                "incident_id": "p9-incident-" + suffix,
                "source_ids": source_ids,
                "assertion": reference["objective"],
                "corroboration_required": len(source_ids) > 1,
            }
        ],
        "parameters": [
            {
                "parameter_id": "seed",
                "value_type": "integer",
                "changes_modeled_values_only": True,
            },
            {
                "parameter_id": "intensity",
                "value_type": "integer",
                "changes_modeled_values_only": True,
            },
        ],
        "integration_recommendation_ids": (
            ["recommend-phase9-dns-lab-ingestion"]
            if DNS_SOURCE_ID in source_ids
            else []
        ),
        "expected_evidence": [
            "GENERATED",
            "ENCODED",
            "RECEIVER_OBSERVED",
            "SPLUNK_DISPATCHED",
            "SPLUNK_OBSERVED",
        ],
        "investigation_recipe_ids": recipe_ids,
        "investigation_steps": [
            {
                "step_id": "{}-guided-{}".format(suffix, index + 1),
                "recipe_id": recipe_ids[recipe_index],
                "title": title,
                "question": title + "?",
                "expected_finding": (
                    reference["objective"]
                    if index < 8
                    else reference["blind_spot"]
                ),
                "explanation": (
                    reference["false_positive"]
                    if index == 6
                    else "Interpret only evidence available from declared sources."
                ),
                "hint": "Keep observation, inference, and verdict separate.",
                "node_ids": ["p9-endpoint", "p9-splunk"],
                "source_ids": source_ids,
            }
            for index, (title, recipe_index) in enumerate(
                zip(guided_titles, guided_recipe_indexes)
            )
        ],
        "validation_expectations": [
            {
                "validation_id": "{}-{}-observed".format(suffix, source_id),
                "label": _source_label(source_id) + " indexed observation",
                "evidence_stage": "SPLUNK_OBSERVED",
                "expected_state": "PROVEN",
                "requirement": "REQUIRED",
                "source_id": source_id,
            }
            for source_id in source_ids
        ],
        "visualization": {"mode": "AUTOMATIC", "direction": "LEFT_TO_RIGHT"},
        "replay_policy": {
            "creates_new_run_id": True,
            "preserves_history": True,
            "reset_to_step": "RUN",
        },
        "troubleshooting_steps": [
            "Validate native receiver evidence before checking HEC.",
            "Use fresh authenticated searches before claiming indexed observation.",
        ],
        "cim_validation": [
            "NOT_ESTABLISHED for Phase 9 DNS and IPFIX security references."
        ],
        "production_replication_guidance": [
            "Map queries to the production resolver or flow integration's documented fields.",
            "Replace NetSpout-only run metadata with time, entity, and source-native correlation.",
        ],
        "security_behavior_stages": [
            "NORMAL",
            "PRECURSOR",
            "SUSPICIOUS_ACTIVITY",
            "CONFIRMED_BEHAVIOR",
            "IMPACT",
            "RECOVERY",
        ],
        "kpi_definitions": kpis,
        "detection_validation": [
            {
                "detection_id": reference["detection_id"],
                "objective": reference["objective"],
                "threat_behavior": reference["family"],
                "mitre_attack_ids": reference["mitre"],
                "required_source_ids": source_ids,
                "required_fields": sorted(
                    {field for kpi in kpis for field in kpi["required_fields"]}
                ),
                "spl": detection_spl,
                "portability": "NETSPOUT_SPECIFIC",
                "baseline_expected_result": "Baseline remains below the modeled incident condition.",
                "incident_expected_result": "Incident records produce the declared bounded deviation.",
                "false_positive_controls": [reference["false_positive"]],
                "blind_spots": [reference["blind_spot"]],
                "validation_outcome": "RUNTIME_VALIDATED",
                "evidence_ids": _reference_evidence(reference),
            }
        ],
        "false_positive_controls": [reference["false_positive"]],
        "known_blind_spots": [reference["blind_spot"]],
        "expected_findings": [
            reference["objective"],
            "Every source must independently prove receiver and Splunk observation.",
        ],
        "scenario_maturity": "SPLUNK_VALIDATED",
    }


def _composition(reference: Dict[str, Any]) -> Dict[str, Any]:
    bindings = []
    for source_id in reference["sources"]:
        if source_id == DNS_SOURCE_ID:
            bindings.append(
                {
                    "source_id": DNS_SOURCE_ID,
                    "generator_id": DNS_GENERATOR_ID,
                    "transport_id": DNS_TRANSPORT_ID,
                    "destination_transport_id": HEC_TRANSPORT_ID,
                    "destination_id": DESTINATION_ID,
                    "runtime_adapter_ref": (
                        "netspout_core.native_runtime.NativeRuntimeFacade.run_dns"
                    ),
                    "receiver_component_id": "bundled-dns-loopback-receiver",
                    "runtime_entity_id": "test-resolver-01",
                    "required": True,
                    "validator_ids": [DNS_VALIDATOR_ID],
                }
            )
        else:
            bindings.append(
                {
                    "source_id": source_id,
                    "generator_id": "generator-native-ipfix",
                    "transport_id": "transport-native-ipfix-udp",
                    "destination_transport_id": HEC_TRANSPORT_ID,
                    "destination_id": DESTINATION_ID,
                    "runtime_adapter_ref": (
                        "netspout_core.native_runtime.NativeRuntimeFacade.run_flow"
                    ),
                    "receiver_component_id": "bundled-ipfix-collector",
                    "runtime_entity_id": "test-endpoint-01",
                    "required": True,
                    "validator_ids": ["validator-native-receiver-boundary"],
                }
            )
    return {
        "composition_id": "compose-" + reference["scenario_id"].lower(),
        "scenario_id": reference["scenario_id"],
        "pack_ids": [PACK_ID],
        "source_bindings": bindings,
        "investigation_recipe_ids": [
            "p9-{}-{}".format(kind, reference["scenario_id"].lower())
            for kind in ("find-incident", "timeline", "analytics", "detection", "validate")
        ],
        "execution_mode": "SINGLE_EVENT",
        "correlate_native_channels": False,
    }


def _reference_evidence(reference: Dict[str, Any]) -> List[str]:
    mapping = {
        "T1498": "EVID-P9-MITRE-NETWORK-DOS",
        "T1071.004": "EVID-P9-MITRE-DNS",
        "T1046": "EVID-P9-MITRE-NETWORK-DISCOVERY",
        "T1048": "EVID-P9-MITRE-EXFIL-ALT-PROTOCOL",
    }
    evidence = [RUNTIME_EVIDENCE_ID, "EVID-P9-IANA-SPECIAL-PURPOSE"]
    if DNS_SOURCE_ID in reference["sources"]:
        evidence.append("EVID-P9-IETF-RFC1035")
    evidence.extend(mapping[item] for item in reference["mitre"])
    return list(dict.fromkeys(evidence))


def _analytic_fields(analytic: str) -> List[str]:
    return {
        "flow-rate": ["timestamp_ms"],
        "destination-concentration": ["dest_ip"],
        "destination-diversity": ["dest_ip"],
        "port-diversity": ["dest_port"],
        "periodicity": ["timestamp_ms", "dest_ip"],
        "byte-packet-distribution": ["bytes", "packets"],
        "dns-query-rate": ["timestamp_ms", "query"],
        "dns-nxdomain-rate": ["response_code"],
        "domain-diversity": ["query"],
        "cross-source-temporal-correlation": ["timestamp_ms", "source_family"],
    }[analytic]


def _analytic_spl(source_ids: List[str]) -> str:
    has_dns = DNS_SOURCE_ID in source_ids
    has_flow = "ietf-ipfix" in source_ids
    if has_dns and not has_flow:
        return (
            " | spath | stats count dc(query) as domain_diversity "
            "sum(eval(response_code=3)) as nxdomain_count by netspout_phase"
        )
    if has_flow and not has_dns:
        return (
            " | spath | stats count dc(dst_addr) as destination_diversity "
            "dc(dst_port) as port_diversity sum(bytes) as bytes "
            "sum(packets) as packets by netspout_phase"
        )
    return (
        " | spath | stats count dc(query) as domain_diversity "
        "dc(dst_addr) as destination_diversity dc(dst_port) as port_diversity "
        "sum(bytes) as bytes by netspout_phase sourcetype"
    )


def _recipe_fields(source_ids: List[str]) -> List[str]:
    fields = ["netspout_phase"]
    if DNS_SOURCE_ID in source_ids:
        fields.extend(["query", "response_code"])
    if "ietf-ipfix" in source_ids:
        fields.extend(["dst_addr", "dst_port", "bytes", "packets"])
    return fields


__all__ = ["DNS_SOURCE_ID", "PACK_ID", "extend_registry"]
