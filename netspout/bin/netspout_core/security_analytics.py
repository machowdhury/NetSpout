"""Field-gated Phase 9 analytics and detection-validation contracts."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, Sequence, Tuple

from netspout_core.security_state import SecurityIncidentPlan, SecurityStage

@dataclass(frozen=True)
class AnalyticDefinition:
    analytic_id: str
    required_source_families: Tuple[str, ...]
    required_fields: Tuple[str, ...]
    description: str
    caveat: str


ANALYTICS: Mapping[str, AnalyticDefinition] = {
    "flow-rate": AnalyticDefinition(
        "flow-rate", ("flow",), ("timestamp_ms",),
        "Count flow starts per bounded interval.",
        "A rate increase is not inherently malicious.",
    ),
    "destination-concentration": AnalyticDefinition(
        "destination-concentration", ("flow",), ("dest_ip",),
        "Measure the largest destination share.",
        "Popular services and load tests may be concentrated.",
    ),
    "destination-diversity": AnalyticDefinition(
        "destination-diversity", ("flow",), ("dest_ip",),
        "Count distinct destinations.",
        "Discovery and approved scanners can create high diversity.",
    ),
    "port-diversity": AnalyticDefinition(
        "port-diversity", ("flow",), ("dest_port",),
        "Count distinct destination ports.",
        "Application clients and scanners can both use many ports.",
    ),
    "periodicity": AnalyticDefinition(
        "periodicity", ("flow",), ("timestamp_ms", "dest_ip"),
        "Measure interval regularity for repeated destination contact.",
        "Monitoring heartbeats and automation can be periodic.",
    ),
    "byte-packet-distribution": AnalyticDefinition(
        "byte-packet-distribution", ("flow",), ("bytes", "packets"),
        "Summarize bytes and packets.",
        "Volume alone does not establish intent.",
    ),
    "dns-query-rate": AnalyticDefinition(
        "dns-query-rate", ("dns",), ("timestamp_ms", "query"),
        "Count DNS queries per bounded interval.",
        "Normal software can produce bursts.",
    ),
    "dns-nxdomain-rate": AnalyticDefinition(
        "dns-nxdomain-rate", ("dns",), ("response_code",),
        "Measure the proportion of NXDOMAIN responses.",
        "NXDOMAIN volume alone does not prove malware.",
    ),
    "domain-diversity": AnalyticDefinition(
        "domain-diversity", ("dns",), ("query",),
        "Count distinct queried names.",
        "Browsers and service discovery may create high diversity.",
    ),
    "cross-source-temporal-correlation": AnalyticDefinition(
        "cross-source-temporal-correlation",
        ("dns", "flow"),
        ("timestamp_ms", "source_family"),
        "Count DNS and flow observations occurring in the same time window.",
        "Temporal proximity is corroboration, not proof of causality.",
    ),
}


def evaluate_analytic(
    analytic_id: str,
    observations: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    definition = ANALYTICS.get(analytic_id)
    if definition is None:
        raise ValueError("unknown security analytic")
    missing = sorted(
        field
        for field in definition.required_fields
        if not observations or any(field not in row for row in observations)
    )
    observed_families = {str(row.get("source_family")) for row in observations}
    missing_families = sorted(
        family
        for family in definition.required_source_families
        if family not in observed_families
    )
    if missing or missing_families:
        return {
            "analytic_id": analytic_id,
            "state": "NOT_APPLICABLE",
            "missing_fields": missing,
            "missing_source_families": missing_families,
            "value": None,
            "caveat": definition.caveat,
        }

    handlers: Dict[str, Callable[[], Any]] = {
        "flow-rate": lambda: _rate(observations),
        "destination-concentration": lambda: _concentration(observations, "dest_ip"),
        "destination-diversity": lambda: len({row["dest_ip"] for row in observations}),
        "port-diversity": lambda: len({row["dest_port"] for row in observations}),
        "periodicity": lambda: _periodicity(observations),
        "byte-packet-distribution": lambda: {
            "bytes_total": sum(int(row["bytes"]) for row in observations),
            "packets_total": sum(int(row["packets"]) for row in observations),
            "bytes_median": statistics.median(int(row["bytes"]) for row in observations),
        },
        "dns-query-rate": lambda: _rate(observations),
        "dns-nxdomain-rate": lambda: (
            sum(int(row["response_code"]) == 3 for row in observations)
            / len(observations)
        ),
        "domain-diversity": lambda: len({row["query"] for row in observations}),
        "cross-source-temporal-correlation": lambda: _cross_source_windows(observations),
    }
    return {
        "analytic_id": analytic_id,
        "state": "EVALUATED",
        "missing_fields": [],
        "missing_source_families": [],
        "value": handlers[analytic_id](),
        "caveat": definition.caveat,
    }


def compare_baseline_incident(
    analytic_id: str,
    baseline: Sequence[Mapping[str, Any]],
    incident: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    return {
        "analytic_id": analytic_id,
        "baseline": evaluate_analytic(analytic_id, baseline),
        "incident": evaluate_analytic(analytic_id, incident),
        "interpretation": (
            "A difference is a modeled deviation and requires contextual corroboration."
        ),
    }


def validate_detection_plan(plan: SecurityIncidentPlan) -> Dict[str, Any]:
    """Validate modeled detection semantics independently of Splunk ingestion."""

    baseline_flows = [_flow_view(row) for row in plan.flows if row.netspout_phase == SecurityStage.NORMAL.value]
    incident_flows = [_flow_view(row) for row in plan.flows if row.netspout_phase != SecurityStage.NORMAL.value]
    baseline_dns = [_dns_view(row) for row in plan.dns if row.stage == SecurityStage.NORMAL]
    incident_dns = [_dns_view(row) for row in plan.dns if row.stage != SecurityStage.NORMAL]
    outcomes: Dict[str, Dict[str, Any]] = {}

    for detection_id in plan.expected_detection_ids:
        if detection_id == "detect-flow-rate-concentration":
            baseline_value = evaluate_analytic("flow-rate", baseline_flows)
            incident_value = evaluate_analytic("flow-rate", incident_flows)
            baseline_match = False
            incident_match = (
                incident_value["state"] == "EVALUATED"
                and baseline_value["state"] == "EVALUATED"
                and incident_value["value"] > baseline_value["value"] * 2
            )
        elif detection_id == "detect-dns-rate-nxdomain-diversity":
            baseline_value = evaluate_analytic("dns-nxdomain-rate", baseline_dns)
            incident_value = evaluate_analytic("dns-nxdomain-rate", incident_dns)
            baseline_match = baseline_value.get("value", 0) > 0.5
            incident_match = incident_value.get("value", 0) > 0.5
        elif detection_id == "detect-periodic-destination-contact":
            baseline_value = evaluate_analytic("periodicity", baseline_flows)
            incident_value = evaluate_analytic("periodicity", incident_flows)
            baseline_match = _periodicity_match(baseline_value)
            incident_match = _periodicity_match(incident_value)
        elif detection_id == "detect-internal-destination-port-diversity":
            baseline_value = {
                "destinations": evaluate_analytic("destination-diversity", baseline_flows),
                "ports": evaluate_analytic("port-diversity", baseline_flows),
            }
            incident_value = {
                "destinations": evaluate_analytic("destination-diversity", incident_flows),
                "ports": evaluate_analytic("port-diversity", incident_flows),
            }
            baseline_match = _diversity_match(baseline_value)
            incident_match = _diversity_match(incident_value)
        elif detection_id == "detect-dns-subdomain-volume":
            baseline_value = evaluate_analytic("domain-diversity", baseline_dns)
            incident_value = evaluate_analytic("domain-diversity", incident_dns)
            baseline_match = bool(baseline_value.get("value", 0) >= 6)
            incident_match = bool(
                incident_value.get("value", 0) >= 6
                and all(row["query"].endswith(".lab-channel.example") for row in incident_dns)
            )
        else:
            raise ValueError("detection has no bounded semantic validator")
        outcomes[detection_id] = {
            "baseline_match": baseline_match,
            "incident_match": incident_match,
            "baseline": baseline_value,
            "incident": incident_value,
            "validated": not baseline_match and incident_match,
        }

    if plan.scenario_id == "SEC-P9-F-CROSS-SOURCE":
        outcomes["detect-cross-source-security-sequence"] = {
            "baseline_match": False,
            "incident_match": all(
                outcomes[item]["incident_match"]
                for item in (
                    "detect-periodic-destination-contact",
                    "detect-internal-destination-port-diversity",
                )
            ),
            "baseline": {"source_families": ["dns", "flow"]},
            "incident": {"ordered_behaviors": ["dns", "periodic-flow", "internal-diversity"]},
        }
        outcomes["detect-cross-source-security-sequence"]["validated"] = bool(
            outcomes["detect-cross-source-security-sequence"]["incident_match"]
        )
    return {
        "scenario_id": plan.scenario_id,
        "state": (
            "RUNTIME_VALIDATED"
            if outcomes and all(item["validated"] for item in outcomes.values())
            else "FAILED"
        ),
        "detections": outcomes,
        "interpretation": (
            "Validation proves deterministic lab behavior only; production thresholds "
            "and malicious intent are not established."
        ),
    }


def _flow_view(row: Any) -> Dict[str, Any]:
    return {
        "source_family": "flow",
        "timestamp_ms": row.start_time_ms,
        "dest_ip": row.dest_ip,
        "dest_port": row.dest_port,
        "bytes": row.bytes_count,
        "packets": row.packets_count,
    }


def _dns_view(row: Any) -> Dict[str, Any]:
    return {
        "source_family": "dns",
        "timestamp_ms": row.timestamp_ms,
        "query": row.qname,
        "response_code": row.rcode,
    }


def _periodicity_match(result: Mapping[str, Any]) -> bool:
    value = result.get("value")
    return bool(
        result.get("state") == "EVALUATED"
        and isinstance(value, Mapping)
        and value.get("sample_count", 0) >= 4
        and value.get("coefficient_of_variation", math.inf) <= 0.1
    )


def _diversity_match(result: Mapping[str, Any]) -> bool:
    destinations = result["destinations"]
    ports = result["ports"]
    return bool(
        destinations.get("state") == "EVALUATED"
        and ports.get("state") == "EVALUATED"
        and destinations.get("value", 0) >= 4
        and ports.get("value", 0) >= 4
    )


def _rate(rows: Sequence[Mapping[str, Any]]) -> float:
    times = [int(row["timestamp_ms"]) for row in rows]
    span_seconds = max(1.0, (max(times) - min(times)) / 1000.0)
    return len(rows) / span_seconds


def _concentration(rows: Sequence[Mapping[str, Any]], field: str) -> float:
    counts: Dict[Any, int] = {}
    for row in rows:
        counts[row[field]] = counts.get(row[field], 0) + 1
    return max(counts.values()) / len(rows)


def _periodicity(rows: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    by_destination: Dict[Any, list] = {}
    for row in rows:
        by_destination.setdefault(row["dest_ip"], []).append(int(row["timestamp_ms"]))
    times = max(by_destination.values(), key=len)
    times.sort()
    intervals = [(right - left) / 1000.0 for left, right in zip(times, times[1:])]
    if len(intervals) < 2:
        return {"sample_count": len(times), "mean_interval_seconds": 0.0, "coefficient_of_variation": math.inf}
    mean = statistics.mean(intervals)
    return {
        "sample_count": len(times),
        "mean_interval_seconds": mean,
        "coefficient_of_variation": statistics.pstdev(intervals) / mean if mean else math.inf,
    }


def _cross_source_windows(rows: Sequence[Mapping[str, Any]]) -> int:
    buckets: Dict[int, set] = {}
    for row in rows:
        bucket = int(row["timestamp_ms"]) // 60_000
        buckets.setdefault(bucket, set()).add(row["source_family"])
    return sum({"dns", "flow"}.issubset(families) for families in buckets.values())


__all__ = [
    "ANALYTICS",
    "AnalyticDefinition",
    "compare_baseline_incident",
    "evaluate_analytic",
    "validate_detection_plan",
]
