import math

import pytest

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.dns_wire import (
    DNS_RCODE_NXDOMAIN,
    DnsWireError,
    build_query,
    build_response,
    execute_loopback_exchange,
    parse_message,
)
from netspout_core.models import TelemetryTransportConfig
from netspout_core.native_runtime import NativeChannel, NativeRuntimeFacade
from netspout_core.security_analytics import (
    ANALYTICS,
    compare_baseline_incident,
    evaluate_analytic,
    validate_detection_plan,
)
from netspout_core.scenario_studio import ScenarioStudioService
from netspout_core.unified_generation import UnifiedGenerationService
from netspout_core.security_state import (
    MAX_DNS_OBSERVATIONS,
    MAX_FLOW_RECORDS,
    SUPPORTED_SECURITY_SCENARIOS,
    SecurityStage,
    build_security_incident_plan,
)


def test_rfc1035_query_response_and_nxdomain_round_trip():
    query = build_query(0x1234, "missing.invalid")
    response = build_response(query, rcode=DNS_RCODE_NXDOMAIN)
    parsed_query = parse_message(query)
    parsed_response = parse_message(response)
    assert not parsed_query.is_response
    assert parsed_query.qname == "missing.invalid"
    assert parsed_response.is_response
    assert parsed_response.transaction_id == parsed_query.transaction_id
    assert parsed_response.rcode == DNS_RCODE_NXDOMAIN
    assert parsed_response.answer_ip is None


def test_rfc1035_loopback_receiver_observes_real_udp_exchange():
    exchange = execute_loopback_exchange(
        transaction_id=42,
        qname="service.example",
        answer_ip="198.51.100.80",
    )
    assert exchange.receiver_query.qname == "service.example"
    assert exchange.client_response.answer_ip == "198.51.100.80"
    assert exchange.query_wire != exchange.response_wire


@pytest.mark.parametrize(
    "name",
    ["", "a" * 64 + ".example", ("a." * 127) + "example"],
)
def test_dns_codec_fails_closed_for_invalid_names(name):
    with pytest.raises(DnsWireError):
        build_query(1, name)


@pytest.mark.parametrize("scenario_id", sorted(SUPPORTED_SECURITY_SCENARIOS))
def test_security_incident_plans_are_deterministic_safe_and_bounded(scenario_id):
    first = build_security_incident_plan(scenario_id, 907, run_id="test-run")
    second = build_security_incident_plan(scenario_id, 907, run_id="test-run")
    assert first == second
    assert len(first.dns) <= MAX_DNS_OBSERVATIONS
    assert len(first.flows) <= MAX_FLOW_RECORDS
    assert first.false_positive_controls
    assert first.blind_spots
    assert all(
        row.src_ip.startswith("192.0.2.")
        and (
            row.dest_ip.startswith("198.51.100.")
            or row.dest_ip.startswith("192.0.2.")
        )
        for row in first.flows
    )
    assert all(
        row.qname.endswith((".example", ".invalid"))
        for row in first.dns
    )


def test_security_plan_unknown_contract_fails_closed():
    with pytest.raises(ValueError, match="no evidence-backed"):
        build_security_incident_plan("unknown-attack", 1, run_id="test-run")
    with pytest.raises(ValueError, match="intensity"):
        build_security_incident_plan(
            "SEC-P9-A-TRAFFIC-FLOOD", 1, run_id="test-run", intensity=100
        )


def test_analytics_require_fields_and_sources_before_evaluation():
    result = evaluate_analytic(
        "dns-nxdomain-rate",
        [{"source_family": "dns", "query": "missing.invalid"}],
    )
    assert result["state"] == "NOT_APPLICABLE"
    assert result["missing_fields"] == ["response_code"]

    cross_source = evaluate_analytic(
        "cross-source-temporal-correlation",
        [{"source_family": "dns", "timestamp_ms": 1}],
    )
    assert cross_source["state"] == "NOT_APPLICABLE"
    assert cross_source["missing_source_families"] == ["flow"]


def test_periodicity_and_baseline_comparison_are_descriptive_not_verdicts():
    rows = [
        {
            "source_family": "flow",
            "timestamp_ms": value * 60_000,
            "dest_ip": "198.51.100.80",
        }
        for value in range(5)
    ]
    result = evaluate_analytic("periodicity", rows)
    assert result["state"] == "EVALUATED"
    assert result["value"]["mean_interval_seconds"] == 60
    assert result["value"]["coefficient_of_variation"] == 0
    comparison = compare_baseline_incident("periodicity", rows[:2], rows)
    assert "requires contextual corroboration" in comparison["interpretation"]
    assert math.isinf(comparison["baseline"]["value"]["coefficient_of_variation"])


def test_required_phase9_analytics_are_declared():
    assert {
        "flow-rate",
        "destination-concentration",
        "destination-diversity",
        "port-diversity",
        "periodicity",
        "byte-packet-distribution",
        "dns-query-rate",
        "dns-nxdomain-rate",
        "domain-diversity",
        "cross-source-temporal-correlation",
    }.issubset(ANALYTICS)


def test_security_behavior_uses_explicit_state_progression():
    plan = build_security_incident_plan(
        "SEC-P9-F-CROSS-SOURCE", 99, run_id="test-run"
    )
    stages = {row.netspout_phase for row in plan.flows}
    assert SecurityStage.NORMAL.value in stages
    assert SecurityStage.SUSPICIOUS_ACTIVITY.value in stages
    assert SecurityStage.CONFIRMED_BEHAVIOR.value in stages


@pytest.mark.parametrize("scenario_id", sorted(SUPPORTED_SECURITY_SCENARIOS))
def test_detection_semantics_separate_baseline_and_incident(scenario_id):
    plan = build_security_incident_plan(scenario_id, 909, run_id="test-run")
    result = validate_detection_plan(plan)
    assert result["state"] == "RUNTIME_VALIDATED"
    assert all(
        not item["baseline_match"] and item["incident_match"]
        for item in result["detections"].values()
    )
    assert "malicious intent" in result["interpretation"]


class _AcceptedDispatcher:
    def __init__(self):
        self.logs = []

    def dispatch_log(self, log, _config):
        self.logs.append(log)
        return {"hec": {"success": True, "message": "accepted"}}


def test_dns_native_runtime_proves_receiver_before_destination_dispatch():
    dispatcher = _AcceptedDispatcher()
    runtime = NativeRuntimeFacade(
        TelemetryTransportConfig(
            hec_enabled=True,
            hec_url="https://127.0.0.1:8088/services/collector",
        ),
        runtime_environment={},
        dispatcher=dispatcher,
    )
    result = runtime.run_dns(
        "test-run",
        "SEC-P9-B-DNS-ANOMALY",
        "test-resolver-01",
        99,
    )
    evidence = {item.stage: item for item in result.evidence}
    assert result.success
    assert evidence["ENCODED"].proven
    assert evidence["RECEIVER_OBSERVED"].proven
    assert evidence["RESPONSE_OBSERVED"].proven
    assert evidence["SPLUNK_DISPATCHED"].proven
    assert not evidence["SPLUNK_OBSERVED"].proven
    assert len(dispatcher.logs) == evidence["GENERATED"].count
    assert all(log.sourcetype == "netspout:dns:wire" for log in dispatcher.logs)
    assert result.raw_artifacts["security_plan"]["scenario_id"] == (
        "SEC-P9-B-DNS-ANOMALY"
    )


def test_phase9_pack_exposes_six_runnable_truthful_security_references():
    service = UnifiedGenerationService(NetSpoutCatalog())
    scenarios = {
        item["scenario_id"]: item
        for item in service.capabilities()["scenarios"]
        if item["scenario_id"].startswith("SEC-P9-")
    }
    assert set(scenarios) == SUPPORTED_SECURITY_SCENARIOS
    for scenario in scenarios.values():
        assert scenario["runnable"]
        assert scenario["verification_state"] == "PARTIALLY_VERIFIED"
        assert scenario["scenario_maturity"] == "SPLUNK_VALIDATED"
        assert scenario["detection_validation"]
        assert scenario["false_positive_controls"]
        assert scenario["known_blind_spots"]
        assert len(scenario["investigation_steps"]) == 10
        assert scenario["cim_validation"] == [
            "NOT_ESTABLISHED for Phase 9 DNS and IPFIX security references."
        ]


def test_phase9_dns_contract_distinguishes_native_and_splunk_contracts():
    source = next(
        item
        for item in UnifiedGenerationService().capabilities()["sources"]
        if item["source_id"] == "ietf-dns-rfc1035"
    )
    assert source["native_contract"]["verification_state"] == "VERIFIED"
    claim = source["splunk_contract"]["sourcetypes"][0]
    assert claim["name"] == "netspout:dns:wire"
    assert claim["authority"] == "NETSPOUT_DEFINED"
    assert source["splunk_contract"]["cim_mappings"] == []
    assert "universal resolver log" in source["known_limitations"][0]


def test_phase9_cross_source_plan_has_stable_identity_across_dns_and_flow():
    plan = build_security_incident_plan(
        "SEC-P9-F-CROSS-SOURCE", 707, run_id="stable-run"
    )
    assert {row.netspout_run_id for row in plan.flows} == {"stable-run"}
    assert {row.netspout_scenario_id for row in plan.flows} == {
        "SEC-P9-F-CROSS-SOURCE"
    }
    assert {row.client_ip for row in plan.dns} == {"192.0.2.25"}
    assert {row.src_ip for row in plan.flows} == {"192.0.2.25"}


def test_scenario_studio_clones_security_reference_without_contract_mutation(tmp_path):
    generation = UnifiedGenerationService()
    studio = ScenarioStudioService(
        generation_service=generation, storage_dir=str(tmp_path)
    )
    clone = studio.clone_scenario("SEC-P9-C-BEACONING")
    assert clone.cloned_from_scenario_id == "SEC-P9-C-BEACONING"
    assert set(clone.source_ids) == {"ietf-dns-rfc1035", "ietf-ipfix"}
    assert clone.contract_fingerprints.keys() == {
        "ietf-dns-rfc1035",
        "ietf-ipfix",
    }
    assert studio.validate_pack(clone).valid
