"""Bounded architecture-gate tests for declarative NetSpout extension packs."""

import copy
import json
import os
import sys
import unittest

from pydantic import ValidationError


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.pack_contracts import PackRegistry


FIXTURE_PATH = os.path.join(
    REPO_ROOT, "tests", "fixtures", "packs", "phase2b_architecture_gate.json"
)
EXTENSION_CATALOG_PATH = os.path.join(REPO_ROOT, "catalog", "extension_packs.json")


def _evidence(evidence_id, provenance):
    return {
        "evidence_id": evidence_id,
        "title": "Non-production architecture fixture",
        "publisher": "NetSpout tests",
        "reference": "repo://tests/fixtures/packs/phase2b_architecture_gate.json",
        "provenance": provenance,
        "verification_state": "PARTIALLY_VERIFIED",
        "notes": "Fixture evidence; it makes no vendor or production-support claim.",
    }


def _source(item):
    source_id = item["source_id"]
    custom = source_id == "fixture-imported-sample"
    provenance = ["VERIFIED_PUBLIC_SAMPLE", "MODELED_VALUE"] if custom else [
        "MODELED_PAYLOAD"
    ]
    evidence_ids = (
        ["EVID-FIXTURE-SAMPLE", "EVID-FIXTURE-MODELED"]
        if custom
        else ["EVID-FIXTURE-MODELED"]
    )
    return {
        "source": {
            "source_id": source_id,
            "vendor": item["vendor"],
            "product": item["product"],
            "product_family": "Architecture fixture",
            "domains": ["netops"],
            "telemetry_source": item["telemetry"],
            "applicable_industries": [],
            "verification_state": "PARTIALLY_VERIFIED",
            "provenance": provenance,
            "evidence_ids": evidence_ids,
            "native_contract": {
                "contract_id": "native-" + source_id,
                "verification_state": "PARTIALLY_VERIFIED",
                "format": "Fixture structure; no production format claim",
                "schema": "Fixture-only structural contract",
                "transports": [],
                "structural_fields": ["fixture_version", "timestamp"],
                "evidence_ids": evidence_ids,
            },
            "splunk_contract": {
                "contract_id": "splunk-" + source_id,
                "verification_state": "PARTIALLY_VERIFIED",
                "input_mechanisms": ["Fixture direct input"],
                "integration_ids": ["fixture-splunk-input"],
                "sourcetypes": [],
                "cim_mappings": [],
                "evidence_ids": ["EVID-FIXTURE-SPLUNK"],
            },
            "netspout_contract": {
                "contract_id": "netspout-" + source_id,
                "verification_state": "PARTIALLY_VERIFIED",
                "schema_classification": "MODELED_VALUE" if custom else "MODELED_PAYLOAD",
                "generator": None,
                "validator": None,
                "transports": [],
                "modeled_fields": ["fixture_value"],
                "structural_fields": ["fixture_version", "timestamp"],
                "scenario_ids": [],
                "generation_modes": ["FIXTURE"],
                "runtime_status": "FIXTURE ONLY",
                "maturity": "DRAFT",
                "evidence_ids": ["EVID-FIXTURE-MODELED"],
            },
            "spl_field_scope": {
                "production_fields": [],
                "netspout_only_fields": ["netspout_run_id"],
                "portable_spl_status": "RESEARCH_REQUIRED",
            },
            "known_limitations": ["Architecture fixture; not production telemetry."],
        },
        "generator_ids": ["generator-" + source_id],
        "validator_ids": ["fixture-contract-validator"],
        "compatible_transport_ids": [
            "fixture-direct",
            "fixture-syslog-udp",
            "fixture-syslog-tcp",
        ],
        "raw_fidelity": {
            "preserve_native_raw": True,
            "modeled_values_may_change": True,
            "structural_mutation_allowed": False,
            "normalization_owner": "SPLUNK_INTEGRATION",
            "cim_validation_stage": "CIM_VERIFIED",
        },
        "custom_lifecycle": "SAMPLE_VERIFIED" if custom else None,
        "sample_derived": custom,
        "ai_assisted_analysis": custom,
        "promotion_authority": "HUMAN_REVIEW_REQUIRED" if custom else None,
    }


def _scenario(item):
    scenario_id = item["scenario_id"]
    source_ids = item["source_ids"]
    node_ids = ["node-{}".format(index) for index in range(len(source_ids))]
    corroborated = scenario_id == "fixture-flow-dns-incident"
    incident_sources = source_ids if corroborated else source_ids[:1]
    return {
        "scenario_id": scenario_id,
        "title": scenario_id,
        "description": "Fixture-only guided scenario",
        "story": "Demonstrates declarative composition without executing telemetry.",
        "difficulty": "ARCHITECTURE_FIXTURE",
        "expected_duration_minutes": 15,
        "learning_objectives": ["Validate extension boundaries"],
        "business_impact": "Not applicable to this non-production fixture",
        "prerequisites": [],
        "technology_ids": ["technology-" + source_id for source_id in source_ids],
        "source_ids": source_ids,
        "entities": node_ids,
        "zones": [{"zone_id": "fixture-zone", "label": "Fixture zone"}],
        "nodes": [
            {
                "node_id": node_id,
                "technology_id": "technology-" + source_id,
                "zone_id": "fixture-zone",
                "role": "fixture",
                "source_ids": [source_id],
            }
            for node_id, source_id in zip(node_ids, source_ids)
        ],
        "relationships": [
            {
                "relationship_id": "relationship-{}".format(index),
                "source_node_id": node_ids[index - 1],
                "target_node_id": node_ids[index],
                "relationship_type": "fixture-dependency",
            }
            for index in range(1, len(node_ids))
        ],
        "telemetry_paths": [
            {
                "path_id": "path-" + source_id,
                "source_id": source_id,
                "producer_node_id": node_id,
                "observer_node_id": None,
            }
            for node_id, source_id in zip(node_ids, source_ids)
        ],
        "incident_path": node_ids,
        "runtime_state_keys": ["health", "load"],
        "timeline": [
            {
                "step_id": "step-" + stage.lower(),
                "stage": stage,
                "description": stage.title(),
                "state_changes": {"phase": stage},
                "incident_ids": ["fixture-incident"] if stage == "INCIDENT" else [],
            }
            for stage in [
                "BASELINE",
                "PRECURSOR",
                "INCIDENT",
                "IMPACT",
                "DETECTION",
                "RECOVERY",
            ]
        ],
        "incidents": [
            {
                "incident_id": "fixture-incident",
                "source_ids": incident_sources,
                "assertion": (
                    "Flow behavior requires DNS corroboration."
                    if corroborated
                    else "Fixture behavior only."
                ),
                "corroboration_required": corroborated,
            }
        ],
        "parameters": [
            {
                "parameter_id": "intensity",
                "value_type": "integer",
                "changes_modeled_values_only": True,
            }
        ],
        "integration_recommendation_ids": [
            "recommend-" + source_id for source_id in source_ids
        ],
        "expected_evidence": ["Raw structure remains unchanged"],
        "investigation_recipe_ids": [
            "fixture-portable-investigation",
            "fixture-run-investigation",
        ],
        "troubleshooting_steps": ["Inspect the declared source contract"],
        "cim_validation": ["Validate only after Splunk parsing"],
        "production_replication_guidance": [
            "Replace fixture contracts with evidence-verified source packs."
        ],
        "curated_layout_ref": None,
    }


def build_registry(fixture):
    technologies = fixture["technologies"]
    source_ids = [item["source_id"] for item in technologies]
    protocol_pack = {
        "pack_id": "fixture-protocol-pack",
        "pack_version": "1.0.0",
        "kind": "PROTOCOL_TELEMETRY",
        "display_name": "Fixture protocol capabilities",
        "maturity": "DRAFT",
        "verification_state": "PARTIALLY_VERIFIED",
        "evidence": [
            _evidence("EVID-FIXTURE-MODELED", "MODELED_PAYLOAD"),
            _evidence("EVID-FIXTURE-SPLUNK", "SPLUNK_DOCUMENTED"),
            _evidence("EVID-FIXTURE-SAMPLE", "VERIFIED_PUBLIC_SAMPLE"),
        ],
        "sources": [],
        "integrations": [
            {
                "integration_id": "fixture-splunk-input",
                "name": "Fixture Splunk input",
                "publisher": "NetSpout tests",
                "integration_type": "TEST_FIXTURE",
                "supported_source_ids": source_ids,
                "splunkbase_id": None,
                "verification_state": "PARTIALLY_VERIFIED",
                "support_state": "FIXTURE_ONLY",
                "sourcetypes": [],
                "cim_mappings": [],
                "netspout_coverage": "PARTIALLY_VERIFIED",
                "evidence_ids": ["EVID-FIXTURE-SPLUNK"],
                "notes": "Not a Technical Add-on or production recommendation.",
            }
        ],
        "generators": [
            {
                "generator_id": "generator-" + source_id,
                "implementation_ref": None,
                "source_ids": [source_id],
                "signals": ["FLOWS"] if source_id == "fixture-netflow" else ["EVENTS"],
                "verification_state": "PARTIALLY_VERIFIED",
                "evidence_ids": ["EVID-FIXTURE-MODELED"],
            }
            for source_id in source_ids
        ],
        "validators": [
            {
                "validator_id": "fixture-contract-validator",
                "implementation_ref": None,
                "source_ids": source_ids,
                "stages": [
                    "RAW_VERIFIED",
                    "SENT",
                    "RECEIVER_OBSERVED",
                    "SPLUNK_OBSERVED",
                    "SOURCETYPE_VERIFIED",
                    "FIELDS_VERIFIED",
                    "CIM_VERIFIED",
                ],
                "evidence_ids": ["EVID-FIXTURE-MODELED"],
            }
        ],
        "transports": [
            {
                "transport_id": "fixture-direct",
                "component": "Fixture adapter",
                "protocol": "Fixture direct protocol",
                "signals": ["EVENTS", "FLOWS"],
                "compatible_source_ids": source_ids,
                "verification_state": "PARTIALLY_VERIFIED",
                "implemented": True,
                "evidence_ids": ["EVID-FIXTURE-MODELED"],
                "notes": "Test-only transport.",
            },
            {
                "transport_id": "fixture-syslog-udp",
                "component": "Syslog sender",
                "protocol": "Syslog/UDP",
                "signals": ["LOGS", "EVENTS"],
                "compatible_source_ids": source_ids,
                "verification_state": "PARTIALLY_VERIFIED",
                "implemented": True,
                "evidence_ids": ["EVID-FIXTURE-MODELED"],
                "notes": "Test-only capability declaration.",
            },
            {
                "transport_id": "fixture-syslog-tcp",
                "component": "Syslog sender",
                "protocol": "Syslog/TCP",
                "signals": ["LOGS", "EVENTS"],
                "compatible_source_ids": source_ids,
                "verification_state": "PARTIALLY_VERIFIED",
                "implemented": True,
                "evidence_ids": ["EVID-FIXTURE-MODELED"],
                "notes": "Test-only capability declaration.",
            },
            {
                "transport_id": "future-otlp",
                "component": "OpenTelemetry Collector",
                "protocol": "OTLP",
                "signals": ["LOGS", "METRICS", "TRACES"],
                "compatible_source_ids": [],
                "verification_state": "RESEARCH_REQUIRED",
                "implemented": False,
                "evidence_ids": ["EVID-FIXTURE-MODELED"],
                "notes": "OTel Collector is the component; OTLP is the protocol.",
            },
            *[
                {
                    "transport_id": transport_id,
                    "component": component,
                    "protocol": protocol,
                    "signals": signals,
                    "compatible_source_ids": [],
                    "verification_state": "RESEARCH_REQUIRED",
                    "implemented": False,
                    "evidence_ids": ["EVID-FIXTURE-MODELED"],
                    "notes": "Architecture capability only; not implemented or supported.",
                }
                for transport_id, component, protocol, signals in [
                    ("future-hec", "HEC sender", "HEC", ["EVENTS"]),
                    ("future-s2s", "Splunk forwarder", "Splunk S2S", ["EVENTS"]),
                    ("future-snmp", "SNMP engine", "SNMP", ["METRICS", "EVENTS"]),
                    ("future-netflow", "Flow exporter", "NetFlow", ["FLOWS"]),
                    ("future-ipfix", "Flow exporter", "IPFIX", ["FLOWS"]),
                    ("future-gnmi", "gNMI client", "gNMI", ["METRICS"]),
                    (
                        "future-vendor-webhook",
                        "Vendor adapter",
                        "HTTPS webhook/API",
                        ["EVENTS"],
                    ),
                ]
            ],
        ],
        "destinations": [
            {
                "destination_id": "fixture-splunk",
                "destination_type": "SPLUNK_FIXTURE",
                "accepted_transport_ids": [
                    "fixture-direct",
                    "fixture-syslog-udp",
                    "fixture-syslog-tcp",
                ],
                "verification_state": "PARTIALLY_VERIFIED",
                "evidence_ids": ["EVID-FIXTURE-SPLUNK"],
            }
        ],
        "integration_recommendations": [
            {
                "recommendation_id": "recommend-" + source_id,
                "source_id": source_id,
                "integration_id": "fixture-splunk-input",
                "requirement": "RESEARCH_REQUIRED",
                "evidence_ids": ["EVID-FIXTURE-SPLUNK"],
                "notes": "Fixture relationship only; production research remains required.",
            }
            for source_id in source_ids
        ],
        "scenarios": [],
        "investigations": [],
        "industries": [],
    }
    vendor_pack = {
        "pack_id": "fixture-vendor-product-pack",
        "pack_version": "1.0.0",
        "kind": "VENDOR_PRODUCT",
        "display_name": "Fixture vendor/product identities",
        "maturity": "DRAFT",
        "verification_state": "PARTIALLY_VERIFIED",
        "dependencies": ["fixture-protocol-pack"],
        "evidence": [],
        "sources": [_source(item) for item in technologies],
    }
    investigation_pack = {
        "pack_id": "fixture-investigation-pack",
        "pack_version": "1.0.0",
        "kind": "INVESTIGATION",
        "display_name": "Fixture investigations",
        "maturity": "DRAFT",
        "verification_state": "PARTIALLY_VERIFIED",
        "dependencies": ["fixture-vendor-product-pack"],
        "investigations": [
            {
                "recipe_id": "fixture-portable-investigation",
                "title": "Portable fixture",
                "portability": "PRODUCTION_PORTABLE",
                "spl": "| where verified_production_field=1",
                "source_ids": source_ids,
                "required_fields": ["verified_production_field"],
                "cim_requirements": [],
                "netspout_only_fields": [],
                "evidence_ids": ["EVID-FIXTURE-SPLUNK"],
            },
            {
                "recipe_id": "fixture-run-investigation",
                "title": "NetSpout run fixture",
                "portability": "NETSPOUT_SPECIFIC",
                "spl": "| where netspout_run_id=\"$run_id$\"",
                "source_ids": source_ids,
                "required_fields": [],
                "cim_requirements": [],
                "netspout_only_fields": ["netspout_run_id"],
                "evidence_ids": ["EVID-FIXTURE-MODELED"],
            },
        ],
    }
    scenario_pack = {
        "pack_id": "fixture-scenario-pack",
        "pack_version": "1.0.0",
        "kind": "SCENARIO",
        "display_name": "Fixture guided scenarios",
        "maturity": "DRAFT",
        "verification_state": "PARTIALLY_VERIFIED",
        "dependencies": [
            "fixture-vendor-product-pack",
            "fixture-investigation-pack",
        ],
        "scenarios": [_scenario(item) for item in fixture["scenarios"]],
    }
    industry_pack = {
        "pack_id": "fixture-industry-pack",
        "pack_version": "1.0.0",
        "kind": "INDUSTRY",
        "display_name": "Fixture industry associations",
        "maturity": "PLANNED",
        "verification_state": "RESEARCH_REQUIRED",
        "dependencies": ["fixture-scenario-pack"],
        "industries": [
            {
                "industry_id": "fixture-banking",
                "name": "Banking fixture",
                "source_ids": ["fixture-cisco-ios-xe", "fixture-microsoft-entra"],
                "scenario_ids": ["fixture-mixed-vendor"],
            },
            {
                "industry_id": "fixture-healthcare",
                "name": "Healthcare fixture",
                "source_ids": ["fixture-cisco-ios-xe", "fixture-microsoft-entra"],
                "scenario_ids": ["fixture-mixed-vendor"],
            },
        ],
    }
    packs = [
        protocol_pack,
        vendor_pack,
        investigation_pack,
        scenario_pack,
        industry_pack,
    ]
    all_pack_ids = [item["pack_id"] for item in packs]

    def composition(composition_id, scenario_id, transport_overrides=None):
        scenario = next(
            item for item in fixture["scenarios"] if item["scenario_id"] == scenario_id
        )
        transport_overrides = transport_overrides or {}
        return {
            "composition_id": composition_id,
            "scenario_id": scenario_id,
            "pack_ids": all_pack_ids,
            "source_bindings": [
                {
                    "source_id": source_id,
                    "generator_id": "generator-" + source_id,
                    "transport_id": transport_overrides.get(
                        source_id, "fixture-direct"
                    ),
                    "destination_id": "fixture-splunk",
                    "validator_ids": ["fixture-contract-validator"],
                }
                for source_id in scenario["source_ids"]
            ],
            "investigation_recipe_ids": [
                "fixture-portable-investigation",
                "fixture-run-investigation",
            ],
        }

    compositions = [
        composition("fixture-cisco-composition", "fixture-cisco-multi-product"),
        composition("fixture-mixed-composition", "fixture-mixed-vendor"),
        composition("fixture-flow-dns-composition", "fixture-flow-dns-incident"),
    ]
    for variant in fixture["transport_variants"]:
        compositions.append(
            composition(
                variant["composition_id"],
                "fixture-transport-neutral",
                {"fixture-cisco-ios-xe": variant["transport_id"]},
            )
        )
    return {
        "schema_version": "1.0.0",
        "registry_version": "phase2b-test-fixture",
        "packs": packs,
        "compositions": compositions,
    }


class TestPhase2BExtensibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE_PATH, "r", encoding="utf-8") as fixture_file:
            cls.fixture = json.load(fixture_file)
        cls.raw_registry = build_registry(cls.fixture)
        cls.registry = PackRegistry.model_validate(cls.raw_registry)
        cls.resources = cls.registry._resources()

    def test_01_existing_phase2_catalog_and_phase3_registry_validate(self):
        catalog = NetSpoutCatalog(catalog_dir=os.path.join(REPO_ROOT, "catalog"))
        self.assertEqual(catalog.get_telemetry_catalog_summary()["source_count"], 11)
        registry = catalog.get_extension_pack_registry()
        self.assertEqual(len(registry["packs"]), 5)
        self.assertEqual(len(registry["compositions"]), 6)
        self.assertIn(
            "cisco-phase8c-domain-references",
            {item["pack_id"] for item in registry["packs"]},
        )
        self.assertEqual(
            registry["catalog_source_bindings"][0]["source_id"],
            "ietf-syslog-rfc5424",
        )

    def test_02_all_five_pack_kinds_are_declarative(self):
        self.assertEqual(
            {item.kind.value for item in self.registry.packs},
            {
                "VENDOR_PRODUCT",
                "PROTOCOL_TELEMETRY",
                "SCENARIO",
                "INVESTIGATION",
                "INDUSTRY",
            },
        )

    def test_03_cisco_multi_product_and_channels(self):
        scenario = next(
            item
            for item in self.resources["scenarios"]
            if item.scenario_id == "fixture-cisco-multi-product"
        )
        sources = {
            item.source.source_id: item.source
            for item in self.resources["source_entries"]
        }
        selected = [sources[source_id] for source_id in scenario.source_ids]
        self.assertEqual({item.vendor for item in selected}, {"Cisco"})
        self.assertEqual(len({item.product for item in selected}), 3)
        self.assertEqual(len({item.telemetry_source for item in selected}), 3)

    def test_04_mixed_vendor_has_no_vendor_branching(self):
        scenario = next(
            item
            for item in self.resources["scenarios"]
            if item.scenario_id == "fixture-mixed-vendor"
        )
        sources = {
            item.source.source_id: item.source
            for item in self.resources["source_entries"]
        }
        self.assertGreaterEqual(
            len({sources[source_id].vendor for source_id in scenario.source_ids}), 3
        )
        contracts_path = os.path.join(
            REPO_ROOT, "src", "netspout_core", "pack_contracts.py"
        )
        with open(contracts_path, "r", encoding="utf-8") as contracts_file:
            contracts = contracts_file.read()
        self.assertNotIn('vendor == "Cisco"', contracts)
        self.assertNotIn('vendor == "Palo Alto', contracts)

    def test_05_flow_and_dns_corroborate_one_incident(self):
        scenario = next(
            item
            for item in self.resources["scenarios"]
            if item.scenario_id == "fixture-flow-dns-incident"
        )
        incident = scenario.incidents[0]
        self.assertEqual(set(incident.source_ids), {"fixture-netflow", "fixture-dns"})
        self.assertTrue(incident.corroboration_required)
        self.assertIn("corroboration", incident.assertion.lower())

    def test_06_imported_sample_is_not_vendor_verified(self):
        entry = next(
            item
            for item in self.resources["source_entries"]
            if item.source.source_id == "fixture-imported-sample"
        )
        self.assertTrue(entry.sample_derived)
        self.assertTrue(entry.ai_assisted_analysis)
        self.assertEqual(entry.custom_lifecycle.value, "SAMPLE_VERIFIED")
        self.assertEqual(entry.promotion_authority.value, "HUMAN_REVIEW_REQUIRED")
        self.assertNotIn(
            "VENDOR_DOCUMENTED", {item.value for item in entry.source.provenance}
        )

    def test_07_scenario_is_unchanged_across_transport_compositions(self):
        variants = [
            item
            for item in self.registry.compositions
            if item.scenario_id == "fixture-transport-neutral"
        ]
        self.assertEqual(len(variants), 2)
        self.assertEqual(
            {item.source_bindings[0].transport_id for item in variants},
            {"fixture-syslog-udp", "fixture-syslog-tcp"},
        )
        self.assertFalse(hasattr(
            next(
                item
                for item in self.resources["scenarios"]
                if item.scenario_id == "fixture-transport-neutral"
            ),
            "transport_id",
        ))

    def test_08_otel_component_protocol_and_all_signals_are_distinct(self):
        otlp = next(
            item
            for item in self.resources["transports"]
            if item.transport_id == "future-otlp"
        )
        self.assertEqual(otlp.component, "OpenTelemetry Collector")
        self.assertEqual(otlp.protocol, "OTLP")
        self.assertEqual(
            {item.value for item in otlp.signals}, {"LOGS", "METRICS", "TRACES"}
        )
        self.assertTrue(
            {
                "HEC",
                "Splunk S2S",
                "Syslog/UDP",
                "Syslog/TCP",
                "OTLP",
                "SNMP",
                "NetFlow",
                "IPFIX",
                "gNMI",
                "HTTPS webhook/API",
            }.issubset({item.protocol for item in self.resources["transports"]})
        )

    def test_09_raw_fidelity_and_post_ingestion_cim_are_enforced(self):
        entry = self.resources["source_entries"][0]
        self.assertTrue(entry.raw_fidelity.preserve_native_raw)
        self.assertFalse(entry.raw_fidelity.structural_mutation_allowed)
        validator = self.resources["validators"][0]
        self.assertEqual(validator.stages[0].value, "RAW_VERIFIED")
        self.assertEqual(validator.stages[-1].value, "CIM_VERIFIED")

        candidate = copy.deepcopy(self.raw_registry)
        candidate["packs"][1]["sources"][0]["raw_fidelity"][
            "structural_mutation_allowed"
        ] = True
        with self.assertRaisesRegex(ValidationError, "preserve the native raw"):
            PackRegistry.model_validate(candidate)

    def test_10_recommendations_are_explicit_and_evidence_backed(self):
        for recommendation in self.resources["recommendations"]:
            self.assertTrue(recommendation.evidence_ids)
            self.assertIsNotNone(recommendation.integration_id)

        candidate = copy.deepcopy(self.raw_registry)
        candidate["packs"][0]["integration_recommendations"][0]["evidence_ids"] = []
        with self.assertRaisesRegex(ValidationError, "require evidence"):
            PackRegistry.model_validate(candidate)

    def test_11_investigation_portability_is_unambiguous(self):
        recipes = {
            item.portability.value: item for item in self.resources["investigations"]
        }
        self.assertFalse(recipes["PRODUCTION_PORTABLE"].netspout_only_fields)
        self.assertEqual(
            recipes["NETSPOUT_SPECIFIC"].netspout_only_fields,
            ["netspout_run_id"],
        )

    def test_12_guided_manifest_drives_topology_and_lifecycle(self):
        scenario = self.resources["scenarios"][0]
        self.assertTrue(scenario.nodes)
        self.assertTrue(scenario.zones)
        self.assertTrue(scenario.relationships)
        self.assertTrue(scenario.telemetry_paths)
        self.assertEqual(
            [item.stage.value for item in scenario.timeline],
            [
                "BASELINE",
                "PRECURSOR",
                "INCIDENT",
                "IMPACT",
                "DETECTION",
                "RECOVERY",
            ],
        )
        self.assertTrue(all(
            item.changes_modeled_values_only for item in scenario.parameters
        ))

    def test_13_industries_reuse_source_contract_ids(self):
        industries = self.resources["industries"]
        self.assertEqual(industries[0].source_ids, industries[1].source_ids)
        all_source_ids = [
            item.source.source_id for item in self.resources["source_entries"]
        ]
        self.assertEqual(len(all_source_ids), len(set(all_source_ids)))

    def test_14_research_required_source_fails_closed_in_composition(self):
        candidate = copy.deepcopy(self.raw_registry)
        source = candidate["packs"][1]["sources"][0]["source"]
        source["verification_state"] = "RESEARCH_REQUIRED"
        source["netspout_contract"]["verification_state"] = "RESEARCH_REQUIRED"
        source["netspout_contract"]["runtime_status"] = "RESEARCH REQUIRED"
        with self.assertRaisesRegex(ValidationError, "non-runnable source"):
            PackRegistry.model_validate(candidate)

    def test_15_duplicate_and_unknown_references_fail_closed(self):
        duplicate = copy.deepcopy(self.raw_registry)
        duplicate["packs"][1]["sources"].append(
            copy.deepcopy(duplicate["packs"][1]["sources"][0])
        )
        with self.assertRaises(ValidationError):
            PackRegistry.model_validate(duplicate)

        unknown = copy.deepcopy(self.raw_registry)
        unknown["compositions"][0]["pack_ids"].append("missing-pack")
        with self.assertRaisesRegex(ValidationError, "unknown values"):
            PackRegistry.model_validate(unknown)

        cycle = copy.deepcopy(self.raw_registry)
        cycle["packs"][0]["dependencies"] = ["fixture-industry-pack"]
        with self.assertRaisesRegex(ValidationError, "dependency cycle"):
            PackRegistry.model_validate(cycle)

    def test_16_models_do_not_execute_implementation_references(self):
        contracts_path = os.path.join(
            REPO_ROOT, "src", "netspout_core", "pack_contracts.py"
        )
        with open(contracts_path, "r", encoding="utf-8") as contracts_file:
            contracts = contracts_file.read()
        for forbidden in [
            "importlib",
            "scenario_runner",
            "telemetry_dispatcher",
            "SplunkLogEngine",
        ]:
            self.assertNotIn(forbidden, contracts)

    def test_17_native_source_and_destination_transports_are_distinct(self):
        with open(EXTENSION_CATALOG_PATH, "r", encoding="utf-8") as catalog_file:
            raw = json.load(catalog_file)
        registry = PackRegistry.model_validate(raw)
        composition = next(
            item
            for item in registry.compositions
            if item.composition_id
            == "compose-test-correlated-interface-degradation-local"
        )

        self.assertEqual(len(composition.source_bindings), 3)
        self.assertEqual(
            {item.source_id for item in composition.source_bindings},
            {
                "cisco-ios-xr-interface-syslog",
                "ietf-snmpv2c-ifmib",
                "openconfig-gnmi-interfaces",
            },
        )
        for binding in composition.source_bindings:
            self.assertTrue(binding.required)
            self.assertTrue(binding.transport_id.startswith("transport-native-"))
            self.assertEqual(
                binding.destination_transport_id,
                "transport-local-hec",
            )
            self.assertNotEqual(
                binding.transport_id,
                binding.destination_transport_id,
            )
            self.assertEqual(
                binding.destination_id,
                "destination-local-docker-splunk",
            )
            self.assertTrue(binding.runtime_adapter_ref)
            self.assertTrue(binding.receiver_component_id)

    def test_18_invalid_native_and_destination_transports_fail_closed(self):
        with open(EXTENSION_CATALOG_PATH, "r", encoding="utf-8") as catalog_file:
            raw = json.load(catalog_file)
        composition_index = next(
            index
            for index, item in enumerate(raw["compositions"])
            if item["composition_id"]
            == "compose-test-correlated-interface-degradation-local"
        )

        native_transport_as_destination = copy.deepcopy(raw)
        binding = native_transport_as_destination["compositions"][composition_index][
            "source_bindings"
        ][0]
        binding["destination_transport_id"] = binding["transport_id"]
        with self.assertRaises(ValidationError):
            PackRegistry.model_validate(native_transport_as_destination)

        unknown_native = copy.deepcopy(raw)
        unknown_native["compositions"][composition_index]["source_bindings"][0][
            "transport_id"
        ] = "transport-missing-native"
        with self.assertRaisesRegex(ValidationError, "unknown values"):
            PackRegistry.model_validate(unknown_native)

        unknown_destination = copy.deepcopy(raw)
        unknown_destination["compositions"][composition_index]["source_bindings"][0][
            "destination_transport_id"
        ] = "transport-missing-destination"
        with self.assertRaisesRegex(ValidationError, "unknown values"):
            PackRegistry.model_validate(unknown_destination)

    def test_19_correlated_scenario_uses_reserved_identity_and_receiver_paths(self):
        with open(EXTENSION_CATALOG_PATH, "r", encoding="utf-8") as catalog_file:
            raw = json.load(catalog_file)
        registry = PackRegistry.model_validate(raw)
        scenario = next(
            item
            for item in registry._resources()["scenarios"]
            if item.scenario_id == "test-correlated-interface-degradation"
        )

        self.assertEqual(
            set(scenario.source_ids),
            {
                "cisco-ios-xr-interface-syslog",
                "ietf-snmpv2c-ifmib",
                "openconfig-gnmi-interfaces",
            },
        )
        self.assertEqual(
            scenario.entities,
            ["cisco-asr9k-pe1", "HundredGigE0/0/0/1"],
        )
        self.assertEqual(
            [step.stage.value for step in scenario.timeline],
            ["BASELINE", "DEGRADE", "FAILOVER", "RECOVERY"],
        )
        self.assertTrue(
            all(
                path.observer_node_id.startswith("bundled-")
                for path in scenario.telemetry_paths
            )
        )
        self.assertEqual(
            {path.source_id for path in scenario.telemetry_paths},
            {
                "cisco-ios-xr-interface-syslog",
                "ietf-snmpv2c-ifmib",
                "openconfig-gnmi-interfaces",
            },
        )
        scenario_text = json.dumps(scenario.model_dump(mode="json"))
        self.assertIn("bundled-syslog-receiver", scenario_text)
        self.assertNotIn("bundled-ipfix-collector", scenario_text)


if __name__ == "__main__":
    unittest.main()
