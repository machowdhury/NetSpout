"""Register the Phase 4C recovery scenarios in the canonical catalog.

Idempotent: re-running replaces the three entries in place rather than appending
duplicates. Authors into ``catalog/scenarios.json`` only; mirrors are produced by
``scripts/sync_core.py``.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = os.path.join(REPO, "catalog", "scenarios.json")

SCENARIOS = [
    {
        "id": "paloalto_threat_investigation",
        "code": "PAN-T1",
        "name": "Palo Alto Networks Threat Investigation",
        "display_name": "Palo Alto Networks Threat Investigation",
        "category": "SECURITY",
        "ecosystem": "mixed_vendor",
        "maturity": "E2E_VALIDATED",
        "description": (
            "Native PAN-OS traffic, threat and system syslog records move a "
            "firewall through baseline, suspicious activity, detection, "
            "containment and recovery, so an analyst can pivot from a high "
            "severity threat verdict back to the correlated traffic sessions."
        ),
        "attack_vector": "Exploitation attempt detected by PAN-OS threat engine",
        "defense_mechanism": (
            "PAN-OS security policy denies the session and the rule base drops "
            "follow-on beacon traffic during containment."
        ),
        "generation_mode": "SCENARIO_DERIVED",
        "sourcetypes": ["pan:traffic", "pan:threat", "pan:system"],
        "default_topology_id": "mixed_edge",
        "topology_id": "mixed_edge",
        "difficulty": "INTERMEDIATE",
        "estimated_duration_sec": 40,
        "vendor_scope": ["palo_alto"],
        "telemetry_requirements": ["syslog"],
        "generation_modes": ["SCENARIO_DERIVED"],
        "affected_entities": ["palo_alto"],
        "expected_observations": [
            "pan:threat records with high or critical severity in the detection phase",
            "pan:traffic records showing deny or drop actions during containment",
            "pan:system records escalating to critical severity in containment"
        ],
        "expected_phases": [
            "baseline", "trigger_event", "telemetry_spike",
            "policy_enforcement", "steady_state"
        ],
        "telemetry_model": "PAN-OS Native CSV Syslog",
        "transport_protocol": "Splunk HEC",
        "splunk_storage": "Event Index (idx_network_ops)",
        "fidelity_badge": "MODELED PAYLOAD",
        "telemetry_notes": (
            "Records are emitted in native PAN-OS CSV syslog layout pinned to the "
            "frozen reference samples (traffic 54 fields, threat 45, system 17). "
            "LEEF and CEF are customer-configured export templates and are not "
            "produced or represented here as native PAN-OS."
        ),
        "timing_claim": None,
        "timing_value": None,
        "timing_unit": None,
        "timing_classification": "NOT_APPLICABLE",
        "timing_notes": None,
        "phases": [
            {
                "phase": "BASELINE",
                "name": "Nominal Perimeter Traffic",
                "duration_ticks": 2,
                "description": "Allow-dominated sessions with informational system logs.",
                "expected_observations": ["Mostly allow actions", "informational system severity"]
            },
            {
                "phase": "DEGRADE",
                "name": "Suspicious Sessions Appear",
                "duration_ticks": 2,
                "description": "Inbound attempts from documentation-space sources begin to be denied.",
                "expected_observations": ["First threat records", "rising deny share"]
            },
            {
                "phase": "FAULT",
                "name": "Threat Detection",
                "duration_ticks": 3,
                "description": "PAN-OS threat engine raises high and critical severity verdicts.",
                "expected_observations": ["high or critical severity threats", "correlated denied sessions"]
            },
            {
                "phase": "FAILOVER",
                "name": "Containment Enforcement",
                "duration_ticks": 2,
                "description": "Security policy drops the flow and system logs go critical.",
                "expected_observations": ["deny/drop dominant traffic", "critical system severity"]
            },
            {
                "phase": "RECOVER",
                "name": "Return To Nominal",
                "duration_ticks": 2,
                "description": "Traffic returns to allow-dominated with informational system logs.",
                "expected_observations": ["allow actions restored", "informational system severity"]
            }
        ]
    },
    {
        "id": "network_security_correlation",
        "code": "XSRC-1",
        "name": "Network Degradation With Security Correlation",
        "display_name": "Network Degradation With Security Correlation",
        "category": "MIXED",
        "ecosystem": "mixed_vendor",
        "maturity": "E2E_VALIDATED",
        "description": (
            "Cisco interface degradation, SNMP-derived performance metrics and "
            "Palo Alto Networks security telemetry land in the same incident "
            "window so a capacity symptom can be correlated with the security "
            "event that produced it."
        ),
        "attack_vector": "Traffic surge that degrades an interface and triggers firewall denies",
        "defense_mechanism": (
            "PAN-OS policy enforcement limits the surge while interface and queue "
            "metrics evidence the degradation on the Cisco side."
        ),
        "generation_mode": "SCENARIO_DERIVED",
        "sourcetypes": [
            "cisco:catalyst:security:events", "pan:traffic", "pan:threat",
            "pan:system", "sc4snmp:metric"
        ],
        "default_topology_id": "mixed_edge",
        "topology_id": "mixed_edge",
        "difficulty": "ADVANCED",
        "estimated_duration_sec": 45,
        "vendor_scope": ["cisco_catalyst", "palo_alto"],
        "telemetry_requirements": ["syslog", "snmp"],
        "generation_modes": ["SCENARIO_DERIVED"],
        "affected_entities": ["cisco_catalyst", "palo_alto"],
        "expected_observations": [
            "Cisco syslog interface error during detection and containment phases",
            "pan:threat security verdicts in the same run",
            "SNMP interface counters and gauges as metric series in the metrics index"
        ],
        "expected_phases": [
            "baseline", "trigger_event", "telemetry_spike",
            "policy_enforcement", "steady_state"
        ],
        "telemetry_model": "Cisco Syslog + PAN-OS Syslog + SNMP Metrics",
        "transport_protocol": "Splunk HEC",
        "splunk_storage": "Event Index (idx_network_ops) + Metrics Index (idx_performance_metrics)",
        "fidelity_badge": "MODELED PAYLOAD",
        "telemetry_notes": (
            "SNMP values are synthetic measurements produced from a typed OID "
            "registry and delivered over the existing HEC metric path. They are "
            "modeled telemetry, not evidence that a live device was polled."
        ),
        "timing_claim": None,
        "timing_value": None,
        "timing_unit": None,
        "timing_classification": "NOT_APPLICABLE",
        "timing_notes": None,
        "phases": [
            {
                "phase": "BASELINE",
                "name": "Healthy Link And Quiet Policy",
                "duration_ticks": 2,
                "description": "Interface errors at zero, allow-dominated traffic.",
                "expected_observations": ["no interface error syslog", "allow dominated traffic"]
            },
            {
                "phase": "DEGRADE",
                "name": "Surge Begins",
                "duration_ticks": 2,
                "description": "First denies and rising interface utilisation.",
                "expected_observations": ["first threat records", "interface counters rising"]
            },
            {
                "phase": "FAULT",
                "name": "Correlated Degradation And Security Event",
                "duration_ticks": 3,
                "description": "Cisco interface error and PAN-OS critical threats in one window.",
                "expected_observations": ["interface error syslog", "high or critical threats"]
            },
            {
                "phase": "FAILOVER",
                "name": "Policy Enforcement",
                "duration_ticks": 2,
                "description": "Firewall denies dominate while the link recovers.",
                "expected_observations": ["deny/drop dominant", "critical system severity"]
            },
            {
                "phase": "RECOVER",
                "name": "Steady State Restored",
                "duration_ticks": 2,
                "description": "Traffic returns to nominal with no new threats.",
                "expected_observations": ["no threats", "allow dominated traffic"]
            }
        ]
    },
    {
        "id": "payment_processing_degradation",
        "code": "FIN-P1",
        "name": "Financial Services Payment Application Degradation",
        "display_name": "Financial Services Payment Application Degradation",
        "category": "INDUSTRY_VERTICAL",
        "ecosystem": "mixed_vendor",
        "maturity": "E2E_VALIDATED",
        "description": (
            "A payment-processing path degrades under denied sessions and "
            "inspection latency, combining PAN-OS security telemetry with Cisco "
            "interface evidence and SNMP performance metrics so the business "
            "impact and its security cause can be read together."
        ),
        "attack_vector": "Exploitation attempt against the payment edge causing session denial",
        "defense_mechanism": (
            "PAN-OS inspection denies the offending sessions while queue and "
            "interface metrics show the resulting latency and loss."
        ),
        "generation_mode": "SCENARIO_DERIVED",
        "sourcetypes": [
            "pan:traffic", "pan:threat", "pan:system",
            "cisco:catalyst:security:events", "sc4snmp:metric"
        ],
        "default_topology_id": "mixed_edge",
        "topology_id": "mixed_edge",
        "difficulty": "ADVANCED",
        "estimated_duration_sec": 50,
        "vendor_scope": ["palo_alto", "cisco_catalyst"],
        "telemetry_requirements": ["syslog", "snmp"],
        "generation_modes": ["SCENARIO_DERIVED"],
        "affected_entities": ["palo_alto", "cisco_catalyst"],
        "expected_observations": [
            "pan:threat records naming a payment-relevant signature",
            "denied pan:traffic sessions during containment",
            "SNMP interface and queue metrics degrading then recovering"
        ],
        "expected_phases": [
            "baseline", "trigger_event", "telemetry_spike",
            "policy_enforcement", "steady_state"
        ],
        "telemetry_model": "PAN-OS Syslog + Cisco Syslog + SNMP Metrics",
        "transport_protocol": "Splunk HEC",
        "splunk_storage": "Event Index (idx_network_ops) + Metrics Index (idx_performance_metrics)",
        "fidelity_badge": "MODELED PAYLOAD",
        "telemetry_notes": (
            "Industry scenario modeled for a financial-services payment path. "
            "Contains no customer data: addresses are from RFC 5737 "
            "documentation space and RFC 1918 ranges only."
        ),
        "timing_claim": None,
        "timing_value": None,
        "timing_unit": None,
        "timing_classification": "NOT_APPLICABLE",
        "timing_notes": None,
        "phases": [
            {
                "phase": "BASELINE",
                "name": "Nominal Authorisation Flow",
                "duration_ticks": 2,
                "description": "Payment sessions allowed with informational system logs.",
                "expected_observations": ["allow dominated", "informational severity"]
            },
            {
                "phase": "DEGRADE",
                "name": "Latency And First Denials",
                "duration_ticks": 2,
                "description": "Inspection begins denying sessions.",
                "expected_observations": ["rising deny share", "first threat verdicts"]
            },
            {
                "phase": "FAULT",
                "name": "Payment Path Degraded",
                "duration_ticks": 3,
                "description": "High and critical threats with heavy session denial.",
                "expected_observations": ["high or critical threats", "denied sessions"]
            },
            {
                "phase": "FAILOVER",
                "name": "Containment At The Payment Edge",
                "duration_ticks": 2,
                "description": "Policy drops dominate; system logs critical.",
                "expected_observations": ["drop dominant", "critical system severity"]
            },
            {
                "phase": "RECOVER",
                "name": "Authorisation Flow Restored",
                "duration_ticks": 2,
                "description": "Traffic returns to nominal.",
                "expected_observations": ["allow dominated", "informational severity"]
            }
        ]
    },
]


def main() -> None:
    # Maturity is earned, not asserted. Default to CONTRACTED; only flip to
    # E2E_VALIDATED once --verified is passed after a live runner->HEC->Splunk
    # run has produced counted evidence for these scenarios.
    verified = "--verified" in sys.argv[1:]
    maturity = "E2E_VALIDATED" if verified else "CONTRACTED"

    with open(CANON) as fh:
        rows = json.load(fh)
    if not isinstance(rows, list):
        raise SystemExit("expected catalog/scenarios.json to be a list")

    by_id = {r.get("id"): i for i, r in enumerate(rows)}
    added, replaced = [], []
    for entry in SCENARIOS:
        entry = dict(entry)
        entry["maturity"] = maturity
        idx = by_id.get(entry["id"])
        if idx is None:
            rows.append(entry)
            added.append(entry["id"])
        else:
            rows[idx] = entry
            replaced.append(entry["id"])

    with open(CANON, "w") as fh:
        # indent=1 matches the committed formatting of catalog/scenarios.json, and
        # sync_core.py byte-copies the canonical file to every mirror. Writing a
        # different indent here would produce ~14k lines of whitespace churn in
        # four files and bury the real change during review.
        json.dump(rows, fh, indent=1)
        fh.write("\n")

    print(f"scenarios now in canonical catalog: {len(rows)}")
    print(f"  maturity applied: {maturity}")
    print(f"  added:    {added}")
    print(f"  replaced: {replaced}")


if __name__ == "__main__":
    main()
