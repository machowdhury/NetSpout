"""Deterministic, bounded security behavior shared by Phase 9 telemetry sources.

The model describes behavior and expected observations.  Native DNS and flow
exporters consume this plan independently, so matching records are derived from
one incident rather than assembled after generation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Mapping, Optional, Tuple

from netspout_core.models import FlowRecord


class SecurityStage(str, Enum):
    NORMAL = "NORMAL"
    PRECURSOR = "PRECURSOR"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    CONFIRMED_BEHAVIOR = "CONFIRMED_BEHAVIOR"
    IMPACT = "IMPACT"
    RECOVERY = "RECOVERY"


@dataclass(frozen=True)
class SecurityEntity:
    entity_id: str
    entity_type: str
    address: Optional[str] = None
    zone: Optional[str] = None


@dataclass(frozen=True)
class DnsBehavior:
    timestamp_ms: int
    stage: SecurityStage
    client_ip: str
    resolver_ip: str
    qname: str
    qtype: int = 1
    rcode: int = 0
    answer_ip: Optional[str] = None
    attack_related: bool = False


@dataclass(frozen=True)
class SecurityIncidentPlan:
    scenario_id: str
    seed: int
    incident_id: str
    entities: Tuple[SecurityEntity, ...]
    dns: Tuple[DnsBehavior, ...]
    flows: Tuple[FlowRecord, ...]
    expected_detection_ids: Tuple[str, ...]
    false_positive_controls: Tuple[str, ...]
    blind_spots: Tuple[str, ...]


SCENARIO_ALIASES: Mapping[str, str] = {
    "SEC-P9-A-TRAFFIC-FLOOD": "traffic-flood",
    "SEC-P9-B-DNS-ANOMALY": "dns-anomaly",
    "SEC-P9-C-BEACONING": "beaconing",
    "SEC-P9-D-INTERNAL-RECON": "internal-recon",
    "SEC-P9-E-DNS-TUNNEL": "dns-tunnel",
    "SEC-P9-F-CROSS-SOURCE": "cross-source",
}

SUPPORTED_SECURITY_SCENARIOS = frozenset(SCENARIO_ALIASES)
MAX_DNS_OBSERVATIONS = 32
MAX_FLOW_RECORDS = 32


def build_security_incident_plan(
    scenario_id: str,
    seed: int,
    *,
    run_id: str,
    intensity: int = 1,
) -> SecurityIncidentPlan:
    """Build one safe plan using only IANA documentation ranges and test names."""

    kind = SCENARIO_ALIASES.get(scenario_id)
    if kind is None:
        raise ValueError("security scenario has no evidence-backed behavior profile")
    if intensity < 1 or intensity > 3:
        raise ValueError("security scenario intensity must be between 1 and 3")

    rng = random.Random(seed)
    base_ms = 1_700_000_000_000 + (seed % 10_000) * 1_000
    client = "192.0.2.25"
    resolver = "192.0.2.53"
    external = "198.51.100.80"
    internal_targets = tuple("198.51.100.{}".format(value) for value in range(40, 48))
    entities = (
        SecurityEntity("test-endpoint-01", "host", client, "user"),
        SecurityEntity("test-resolver-01", "dns-resolver", resolver, "services"),
        SecurityEntity("test-external-01", "external-destination", external, "external"),
        SecurityEntity("test-segment-01", "network-segment", "198.51.100.0/24", "internal"),
    )

    dns = []
    flows = []

    def add_dns(
        offset_s: int,
        stage: SecurityStage,
        qname: str,
        *,
        rcode: int = 0,
        answer_ip: Optional[str] = external,
        related: bool = False,
    ) -> None:
        dns.append(
            DnsBehavior(
                timestamp_ms=base_ms + offset_s * 1000,
                stage=stage,
                client_ip=client,
                resolver_ip=resolver,
                qname=qname,
                rcode=rcode,
                answer_ip=answer_ip if rcode == 0 else None,
                attack_related=related,
            )
        )

    def add_flow(
        offset_s: int,
        stage: SecurityStage,
        destination: str,
        port: int,
        *,
        protocol: int = 6,
        packets: int = 8,
        octets: int = 960,
        duration_ms: int = 500,
        related: bool = False,
    ) -> None:
        start = base_ms + offset_s * 1000
        flows.append(
            FlowRecord(
                src_ip=client,
                dest_ip=destination,
                src_port=40_000 + rng.randrange(0, 20_000),
                dest_port=port,
                protocol=protocol,
                tcp_flags=2 if protocol == 6 else 0,
                packets_count=packets,
                bytes_count=octets,
                start_time_ms=start,
                end_time_ms=start + duration_ms,
                netspout_run_id=run_id,
                netspout_scenario_id=scenario_id,
                netspout_phase=stage.value,
                anomaly_type="modeled-indicator" if related else "normal",
            )
        )

    # Every applicable scenario begins with ordinary comparison traffic.
    if kind != "internal-recon":
        for index, name in enumerate(("updates.example", "monitoring.example", "time.example")):
            add_dns(index * 15, SecurityStage.NORMAL, name, related=False)
    for index in range(3):
        add_flow(index * 20, SecurityStage.NORMAL, external, 443, related=False)

    detections: Tuple[str, ...]
    controls: Tuple[str, ...]
    blind_spots: Tuple[str, ...]

    if kind == "traffic-flood":
        for index in range(8 * intensity):
            add_flow(
                120 + index,
                SecurityStage.SUSPICIOUS_ACTIVITY,
                external,
                443,
                packets=150 + index * 4,
                octets=18_000 + index * 500,
                duration_ms=900,
                related=True,
            )
        detections = ("detect-flow-rate-concentration",)
        controls = ("Compare with an approved load test using the same destination.",)
        blind_spots = ("Sampled flows may understate packet rate.", "Flows do not prove service denial.")
    elif kind == "dns-anomaly":
        for index in range(6 * intensity):
            add_dns(
                120 + index * 2,
                SecurityStage.SUSPICIOUS_ACTIVITY,
                "candidate-{:02d}.invalid".format(index),
                rcode=3,
                answer_ip=None,
                related=True,
            )
        detections = ("detect-dns-rate-nxdomain-diversity",)
        controls = ("Compare with software discovery and mistyped-domain activity.",)
        blind_spots = ("NXDOMAIN volume and label shape do not prove malware.",)
    elif kind == "beaconing":
        add_dns(110, SecurityStage.PRECURSOR, "telemetry-channel.example", related=True)
        for index in range(4 * intensity):
            jitter = rng.choice((-2, -1, 0, 1, 2))
            add_flow(
                120 + index * 60 + jitter,
                SecurityStage.SUSPICIOUS_ACTIVITY,
                external,
                443,
                packets=5,
                octets=640,
                duration_ms=250,
                related=True,
            )
        detections = ("detect-periodic-destination-contact",)
        controls = ("Compare with the declared monitoring-agent heartbeat.",)
        blind_spots = ("Encrypted flows reveal timing, not command content.",)
    elif kind == "internal-recon":
        ports = (22, 80, 135, 139, 443, 445, 3389, 5985)
        for index in range(8 * intensity):
            add_flow(
                120 + index,
                SecurityStage.SUSPICIOUS_ACTIVITY,
                internal_targets[index % len(internal_targets)],
                ports[index % len(ports)],
                packets=2,
                octets=120,
                duration_ms=100,
                related=True,
            )
        detections = ("detect-internal-destination-port-diversity",)
        controls = ("Compare with approved vulnerability scanning windows.",)
        blind_spots = ("Connection attempts do not prove successful lateral movement.",)
    elif kind == "dns-tunnel":
        for index in range(6 * intensity):
            label = "{:016x}".format(rng.getrandbits(64))
            add_dns(
                120 + index * 3,
                SecurityStage.SUSPICIOUS_ACTIVITY,
                "{}.lab-channel.example".format(label),
                related=True,
            )
            add_flow(
                120 + index * 3,
                SecurityStage.SUSPICIOUS_ACTIVITY,
                resolver,
                53,
                protocol=17,
                packets=2,
                octets=180 + index,
                duration_ms=50,
                related=True,
            )
        detections = ("detect-dns-subdomain-volume",)
        controls = ("Compare with CDNs, tracking identifiers, and DNS-based service discovery.",)
        blind_spots = ("Synthetic labels are indicators only; no exfiltration is performed or proven.",)
    else:
        add_dns(110, SecurityStage.PRECURSOR, "telemetry-channel.example", related=True)
        for index in range(4 * intensity):
            add_flow(
                120 + index * 60 + rng.choice((-1, 0, 1)),
                SecurityStage.SUSPICIOUS_ACTIVITY,
                external,
                443,
                packets=5,
                octets=640,
                duration_ms=250,
                related=True,
            )
        for index in range(4 * intensity):
            add_flow(
                390 + index,
                SecurityStage.CONFIRMED_BEHAVIOR,
                internal_targets[index % len(internal_targets)],
                (22, 445, 3389, 5985)[index % 4],
                packets=2,
                octets=120,
                duration_ms=100,
                related=True,
            )
        detections = (
            "detect-periodic-destination-contact",
            "detect-internal-destination-port-diversity",
        )
        controls = ("Compare both observations with approved monitoring and scanning activity.",)
        blind_spots = (
            "The sequence supports correlated suspicious behavior, not attribution.",
            "No endpoint execution or identity evidence is modeled.",
        )

    if len(dns) > MAX_DNS_OBSERVATIONS or len(flows) > MAX_FLOW_RECORDS:
        raise ValueError("security behavior exceeded its bounded observation cap")
    return SecurityIncidentPlan(
        scenario_id=scenario_id,
        seed=seed,
        incident_id="incident-{}-{}".format(scenario_id.lower(), seed),
        entities=entities,
        dns=tuple(dns),
        flows=tuple(flows),
        expected_detection_ids=detections,
        false_positive_controls=controls,
        blind_spots=blind_spots,
    )


def security_plan_summary(plan: SecurityIncidentPlan) -> Dict[str, object]:
    return {
        "scenario_id": plan.scenario_id,
        "incident_id": plan.incident_id,
        "seed": plan.seed,
        "entity_ids": [item.entity_id for item in plan.entities],
        "dns_observations": len(plan.dns),
        "flow_observations": len(plan.flows),
        "expected_detection_ids": list(plan.expected_detection_ids),
        "false_positive_controls": list(plan.false_positive_controls),
        "blind_spots": list(plan.blind_spots),
    }


__all__ = [
    "DnsBehavior",
    "MAX_DNS_OBSERVATIONS",
    "MAX_FLOW_RECORDS",
    "SCENARIO_ALIASES",
    "SUPPORTED_SECURITY_SCENARIOS",
    "SecurityEntity",
    "SecurityIncidentPlan",
    "SecurityStage",
    "build_security_incident_plan",
    "security_plan_summary",
]
