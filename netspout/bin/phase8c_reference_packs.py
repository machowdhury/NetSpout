# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/phase8c_reference_packs.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Build the compact Phase 8C reference specification into strict Pack contracts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


PACK_ID = "cisco-phase8c-domain-references"
TRANSPORT_ID = "transport-phase8c-native-syslog-udp"
GENERATOR_ID = "generator-phase8c-declarative-native-template"
RUNTIME_EVIDENCE_ID = "EVID-P8C-NETSPOUT-DECLARATIVE-RUNTIME"


def _source_entry(source: Dict[str, Any]) -> Dict[str, Any]:
    evidence_ids = [*source["evidence_ids"], RUNTIME_EVIDENCE_ID]
    return {
        "source": {
            "source_id": source["source_id"],
            "vendor": source["vendor"],
            "product": source["product"],
            "product_family": source["product_family"],
            "domains": source["domains"],
            "telemetry_source": source["telemetry_source"],
            "applicable_industries": [],
            "verification_state": "PARTIALLY_VERIFIED",
            "provenance": ["VENDOR_DOCUMENTED", "MODELED_PAYLOAD"],
            "evidence_ids": evidence_ids,
            "native_contract": {
                "contract_id": source["contract_id"],
                "verification_state": "VERIFIED",
                "format": source["format"],
                "schema": " ".join(source["structural_fields"]),
                "transports": [
                    {
                        "protocol": "Syslog over UDP",
                        "default_port": 514,
                        "encoding": "UTF-8",
                    }
                ],
                "structural_fields": source["structural_fields"],
                "evidence_ids": source["evidence_ids"],
            },
            "splunk_contract": {
                "contract_id": "splunk-{}".format(source["source_id"]),
                "verification_state": "PARTIALLY_VERIFIED",
                "input_mechanisms": [
                    "Bundled native UDP receiver followed by separate HEC delivery"
                ],
                "integration_ids": [],
                "sourcetypes": [
                    {
                        "name": source["sourcetype"],
                        "authority": "NETSPOUT_DEFINED",
                        "evidence_ids": [RUNTIME_EVIDENCE_ID],
                    }
                ],
                "cim_mappings": [],
                "evidence_ids": [RUNTIME_EVIDENCE_ID],
            },
            "netspout_contract": {
                "contract_id": "netspout-{}".format(source["source_id"]),
                "verification_state": "PARTIALLY_VERIFIED",
                "schema_classification": "NETSPOUT_SCHEMA",
                "generator": GENERATOR_ID,
                "validator": source["validator_id"],
                "transports": [TRANSPORT_ID],
                "modeled_fields": source["modeled_fields"],
                "structural_fields": source["structural_fields"],
                "scenario_ids": [],
                "generation_modes": ["SCENARIO"],
                "runtime_status": "AVAILABLE",
                "maturity": "BETA",
                "evidence_ids": [RUNTIME_EVIDENCE_ID],
            },
            "spl_field_scope": {
                "production_fields": ["_raw", "host", "source", "sourcetype"],
                "netspout_only_fields": [
                    "netspout_run_id",
                    "netspout_scenario_id",
                    "netspout_phase",
                ],
                "portable_spl_status": "RESEARCH_REQUIRED",
            },
            "known_limitations": source["known_limitations"],
        },
        "generator_ids": [GENERATOR_ID],
        "validator_ids": [source["validator_id"]],
        "compatible_transport_ids": [TRANSPORT_ID],
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


def _profile(source: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "profile_id": source["profile_id"],
        "source_id": source["source_id"],
        "format": source["format"],
        "sourcetype": source["sourcetype"],
        "template": source["template"],
        "structural_fields": source["structural_fields"],
        "modeled_fields": source["modeled_fields"],
        "derived_fields": source["derived_fields"],
        "supported_state_keys": source["supported_state_keys"],
        "phase_values": source["phase_values"],
        "phase_templates": source["phase_templates"],
        "evidence_ids": source["evidence_ids"],
    }


def _investigation(reference: Dict[str, Any], source_by_id) -> Dict[str, Any]:
    recipe_id = "investigate-{}-reference".format(
        reference["scenario_id"].lower()
    )
    sourcetypes = [
        source_by_id[source_id]["sourcetype"]
        if source_id in source_by_id
        else "netspout:cisco:iosxr:syslog"
        for source_id in reference["source_ids"]
    ]
    scope = " OR ".join(
        'sourcetype="{}"'.format(value) for value in sourcetypes
    )
    return {
        "recipe_id": recipe_id,
        "title": "Investigate {}".format(reference["title"]),
        "objective": "Order the bounded reference lifecycle by source and phase.",
        "question": "Which source and entity changed first, and was recovery observed?",
        "expected_finding": (
            "All declared sources are scoped to one NetSpout run and retain "
            "their documented source-native raw structures."
        ),
        "explanation": (
            "NetSpout correlation fields scope this lab run; they are not "
            "vendor-native fields."
        ),
        "hint": "Confirm per-source counts and phase order before inferring impact.",
        "portability": "NETSPOUT_SPECIFIC",
        "spl": (
            "search index=idx_network_ops ({}) "
            '| where netspout_run_id="$run_id$" '
            "| stats count by sourcetype, host, netspout_phase"
        ).format(scope),
        "source_ids": reference["source_ids"],
        "required_fields": ["_raw", "host", "sourcetype"],
        "cim_requirements": [],
        "netspout_only_fields": ["netspout_run_id", "netspout_phase"],
        "evidence_ids": reference["evidence_ids"],
    }


def _manifest(reference: Dict[str, Any]) -> Dict[str, Any]:
    scenario_id = reference["scenario_id"]
    recipe_id = "investigate-{}-reference".format(scenario_id.lower())
    device_nodes = []
    relationships = []
    telemetry_paths = []
    for index, source_id in enumerate(reference["source_ids"]):
        entity_id = reference["entity_ids"][index]
        device_nodes.append(
            {
                "node_id": entity_id,
                "technology_id": reference["technology_ids"][index],
                "zone_id": "modeled-source-zone",
                "role": "modeled-source",
                "source_ids": [source_id],
                "label": entity_id,
                "entity_id": entity_id,
                "description": "Reserved fictional identity for bounded lab evidence.",
                "vendor": "Cisco",
            }
        )
        relationships.append(
            {
                "relationship_id": "native-path-{}-{}".format(scenario_id, index),
                "source_node_id": entity_id,
                "target_node_id": "bundled-phase8c-syslog-receiver",
                "relationship_type": "source-native-telemetry",
                "protocol": "Syslog/UDP",
                "purpose": "Terminate the native UDP path before HEC delivery.",
                "telemetry_source_ids": [source_id],
                "incident_relevance": "Carries one documented event family.",
            }
        )
        telemetry_paths.append(
            {
                "path_id": "path-{}-{}".format(scenario_id, index),
                "source_id": source_id,
                "producer_node_id": entity_id,
                "observer_node_id": "bundled-phase8c-syslog-receiver",
                "label": "Native receiver boundary",
                "protocol": "Syslog/UDP",
            }
        )
    nodes = [
        *device_nodes,
        {
            "node_id": "bundled-phase8c-syslog-receiver",
            "technology_id": "syslog-udp",
            "zone_id": "receiver-zone",
            "role": "receiver",
            "source_ids": [],
            "label": "Bundled Syslog Receiver",
            "entity_id": "test-component-phase8c-syslog",
        },
        {
            "node_id": "phase8c-local-splunk",
            "technology_id": "splunk-hec",
            "zone_id": "destination-zone",
            "role": "destination",
            "source_ids": [],
            "label": "TEST Local Splunk",
            "entity_id": "phase8c-local-splunk.invalid",
        },
    ]
    relationships.append(
        {
            "relationship_id": "destination-path-{}".format(scenario_id),
            "source_node_id": "bundled-phase8c-syslog-receiver",
            "target_node_id": "phase8c-local-splunk",
            "relationship_type": "destination-delivery",
            "protocol": "HEC",
            "purpose": "Deliver receiver-observed records to the lab destination.",
            "telemetry_source_ids": reference["source_ids"],
            "incident_relevance": None,
        }
    )
    timeline = []
    stage_states = (
        ("BASELINE", "normal", []),
        ("DEGRADE", "degraded", []),
        ("FAILOVER", "affected", ["incident-{}".format(scenario_id)]),
        ("RECOVERY", "recovered", []),
    )
    for index, (stage, state, incident_ids) in enumerate(stage_states):
        timeline.append(
            {
                "step_id": "{}-{}".format(scenario_id.lower(), stage.lower()),
                "stage": stage,
                "description": "{} lifecycle phase.".format(stage.title()),
                "state_changes": {"service.path": state},
                "entity_state_changes": {
                    entity_id: state for entity_id in reference["entity_ids"]
                },
                "telemetry_state_changes": {
                    source_id: "OBSERVED" if stage == "RECOVERY" else "ACTIVE"
                    for source_id in reference["source_ids"]
                },
                "expected_observations": [
                    "Declared source records preserve their documented structures."
                ],
                "evidence_source_ids": reference["source_ids"],
                "incident_ids": incident_ids,
            }
        )
    return {
        "scenario_id": scenario_id,
        "title": reference["title"],
        "description": reference["technical_description"],
        "story": reference["story"],
        "domain": reference["domain"],
        "category": reference["category"],
        "technical_description": reference["technical_description"],
        "difficulty": "INTERMEDIATE",
        "expected_duration_minutes": 5,
        "learning_objectives": [
            "Separate source-native receiver evidence from HEC destination evidence.",
            "Interpret only claims supported by the attached vendor documentation.",
        ],
        "skills_practiced": ["Raw-event validation", "Ordered incident correlation"],
        "expected_outcome": "The user verifies the bounded lifecycle and its limitations.",
        "baseline_description": "The fictional path begins healthy.",
        "incident_description": "The modeled path degrades before recovery.",
        "discovery_prompt": "Identify the first source transition and verify recovery.",
        "learning_hints": [
            "UDP send is not receiver observation.",
            "NetSpout correlation fields are lab-only metadata.",
        ],
        "business_impact": reference["business_impact"],
        "prerequisites": [
            "Bundled syslog receiver and local test Splunk configured",
            "Environment-provided Splunk credentials for live validation",
        ],
        "technology_ids": reference["technology_ids"],
        "source_ids": reference["source_ids"],
        "entities": reference["entity_ids"],
        "zones": [
            {"zone_id": "modeled-source-zone", "label": "Reserved Test Sources"},
            {"zone_id": "receiver-zone", "label": "Bundled Native Receiver"},
            {"zone_id": "destination-zone", "label": "Test Destination"},
        ],
        "nodes": nodes,
        "relationships": relationships,
        "telemetry_paths": telemetry_paths,
        "incident_path": reference["entity_ids"],
        "incident_summary": "One bounded modeled lifecycle.",
        "runtime_state_keys": ["normal", "degraded", "affected", "recovered"],
        "timeline": timeline,
        "incidents": [
            {
                "incident_id": "incident-{}".format(scenario_id),
                "source_ids": reference["source_ids"],
                "assertion": (
                    "The declared source{} describe{} one modeled lifecycle."
                ).format(
                    "s" if len(reference["source_ids"]) > 1 else "",
                    "" if len(reference["source_ids"]) > 1 else "s",
                ),
                "corroboration_required": len(reference["source_ids"]) > 1,
            }
        ],
        "parameters": [
            {
                "parameter_id": "intensity",
                "value_type": "integer",
                "changes_modeled_values_only": True,
            }
        ],
        "integration_recommendation_ids": [],
        "expected_evidence": [
            "Receiver-observed records for every generated native syslog event.",
            "Separate authenticated Splunk observation scoped to the run identifier.",
        ],
        "investigation_recipe_ids": [recipe_id],
        "investigation_steps": [
            {
                "step_id": "investigate-{}".format(scenario_id.lower()),
                "recipe_id": recipe_id,
                "title": "Order the reference lifecycle",
                "question": "Did every declared source reach recovery?",
                "expected_finding": "All declared sources remain scoped to one run.",
                "explanation": "A shared state clock correlates independent raw sources.",
                "hint": "Compare receiver counts before Splunk counts.",
                "node_ids": [
                    *reference["entity_ids"],
                    "bundled-phase8c-syslog-receiver",
                    "phase8c-local-splunk",
                ],
                "source_ids": reference["source_ids"],
            }
        ],
        "validation_expectations": [
            *[
                {
                    "validation_id": "receiver-{}-{}".format(
                        scenario_id.lower(), index
                    ),
                    "label": "Bundled receiver observed {}".format(source_id),
                    "evidence_stage": "RECEIVER_OBSERVED",
                    "expected_state": "PROVEN",
                    "requirement": "REQUIRED",
                    "source_id": source_id,
                }
                for index, source_id in enumerate(reference["source_ids"])
            ],
            {
                "validation_id": "splunk-{}".format(scenario_id.lower()),
                "label": "Authenticated Splunk search observed the run",
                "evidence_stage": "SPLUNK_OBSERVED",
                "expected_state": "PROVEN",
                "requirement": "REQUIRED",
            },
        ],
        "visualization": {
            "mode": "AUTOMATIC",
            "direction": "LEFT_TO_RIGHT",
            "curated_layout_ref": None,
        },
        "replay_policy": {
            "creates_new_run_id": True,
            "preserves_history": True,
            "reset_to_step": "RUN",
        },
        "troubleshooting_steps": [
            "Verify the native receiver boundary before destination delivery.",
            "Do not infer root cause or attack intent from one event family.",
        ],
        "cim_validation": [],
        "production_replication_guidance": [
            "Use Cisco-supported logging configuration for the exact deployed release.",
            "Validate production sourcetypes, field extractions, and CIM mappings independently.",
            "Replace reserved test identities and NetSpout-only correlation fields.",
        ],
        "troubleshooting_operation_ids": reference["operation_ids"],
        "production_guide_id": reference["production_guide_id"],
        "curated_layout_ref": None,
    }


def _binding(source_id, entity_id, interface_id, source_by_id):
    if source_id == "cisco-ios-xr-interface-syslog":
        return {
            "source_id": source_id,
            "generator_id": "generator-declarative-native-template",
            "transport_id": "transport-native-syslog-udp",
            "destination_transport_id": "transport-local-hec",
            "destination_id": "destination-local-docker-splunk",
            "runtime_adapter_ref": (
                "netspout_core.native_runtime.NativeRuntimeFacade.run_syslog"
            ),
            "payload_profile_id": "template-cisco-ios-xr-link-updown",
            "receiver_component_id": "bundled-syslog-receiver",
            "runtime_entity_id": entity_id,
            "runtime_interface_id": interface_id,
            "required": True,
            "validator_ids": ["validator-ios-xr-interface-syslog"],
        }
    source = source_by_id[source_id]
    return {
        "source_id": source_id,
        "generator_id": GENERATOR_ID,
        "transport_id": TRANSPORT_ID,
        "destination_transport_id": "transport-local-hec",
        "destination_id": "destination-local-docker-splunk",
        "runtime_adapter_ref": (
            "netspout_core.native_runtime.NativeRuntimeFacade.run_syslog"
        ),
        "payload_profile_id": source["profile_id"],
        "receiver_component_id": "bundled-syslog-receiver",
        "runtime_entity_id": entity_id,
        "runtime_interface_id": interface_id,
        "required": True,
        "validator_ids": [source["validator_id"]],
    }


def extend_registry(
    registry: Dict[str, Any], specification: Dict[str, Any]
) -> Dict[str, Any]:
    """Return a merged raw registry; strict validation remains the caller's job."""
    merged = deepcopy(registry)
    source_by_id = {
        item["source_id"]: item for item in specification["sources"]
    }
    source_ids = list(source_by_id)
    investigations = [
        _investigation(reference, source_by_id)
        for reference in specification["references"]
    ]
    pack = {
        "pack_id": PACK_ID,
        "pack_version": "1.0.0",
        "kind": "VENDOR_PRODUCT",
        "display_name": "Cisco Phase 8C Multi-Domain Reference Pack",
        "maturity": "BETA",
        "verification_state": "PARTIALLY_VERIFIED",
        "dependencies": [
            "netspout-rfc5424-generation",
            "netspout-rfc5424-investigation",
            "cisco-ios-xr-coverage",
        ],
        "evidence": specification["evidence"],
        "sources": [_source_entry(item) for item in specification["sources"]],
        "integrations": [],
        "generators": [
            {
                "generator_id": GENERATOR_ID,
                "implementation_ref": "allowlist:declarative-native-template",
                "source_ids": source_ids,
                "signals": ["LOGS", "EVENTS"],
                "verification_state": "PARTIALLY_VERIFIED",
                "evidence_ids": [RUNTIME_EVIDENCE_ID],
            }
        ],
        "validators": [
            {
                "validator_id": item["validator_id"],
                "implementation_ref": (
                    "allowlist:declarative-native-template-validator"
                ),
                "source_ids": [item["source_id"]],
                "stages": [
                    "RAW_VERIFIED",
                    "SENT",
                    "RECEIVER_OBSERVED",
                    "SPLUNK_OBSERVED",
                ],
                "evidence_ids": item["evidence_ids"],
            }
            for item in specification["sources"]
        ],
        "transports": [
            {
                "transport_id": TRANSPORT_ID,
                "component": "Bundled EmbeddedSyslogServer receiver",
                "protocol": "Source-native syslog over UDP",
                "signals": ["LOGS", "EVENTS"],
                "compatible_source_ids": source_ids,
                "verification_state": "PARTIALLY_VERIFIED",
                "implemented": True,
                "evidence_ids": [RUNTIME_EVIDENCE_ID],
                "notes": (
                    "Native UDP terminates at the bundled receiver before "
                    "separate HEC delivery."
                ),
            }
        ],
        "destinations": [],
        "declarative_templates": [
            _profile(item) for item in specification["sources"]
        ],
        "integration_recommendations": [],
        "scenarios": [
            _manifest(reference) for reference in specification["references"]
        ],
        "investigations": investigations,
        "industries": [],
    }
    merged["registry_version"] = specification["registry_version"]
    merged["packs"].append(pack)
    for reference in specification["references"]:
        pack_ids = [PACK_ID]
        if "cisco-ios-xr-interface-syslog" in reference["source_ids"]:
            pack_ids.append("cisco-ios-xr-coverage")
        merged["compositions"].append(
            {
                "composition_id": "compose-{}-phase8c".format(
                    reference["scenario_id"].lower()
                ),
                "scenario_id": reference["scenario_id"],
                "pack_ids": pack_ids,
                "source_bindings": [
                    _binding(source_id, entity_id, interface_id, source_by_id)
                    for source_id, entity_id, interface_id in zip(
                        reference["source_ids"],
                        reference["entity_ids"],
                        reference["interface_ids"],
                    )
                ],
                "investigation_recipe_ids": [
                    "investigate-{}-reference".format(
                        reference["scenario_id"].lower()
                    )
                ],
                "execution_mode": "SHARED_STATE_LIFECYCLE",
                "state_profile_scenario_id": "phase8c-interface-lifecycle",
                "state_entity_id": "node-cat-leaf",
                "state_interface_id": "FortyGigE1/0/1",
                "correlate_native_channels": False,
            }
        )
    return merged


__all__ = ["extend_registry"]
