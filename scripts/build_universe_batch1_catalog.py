"""Universal Vendor Coverage — batch 1 catalog graduation.

Appends the 4 batch-1 vendor rows and the 4 canonical sourcetype rows to the
canonical catalogs (idempotent), plus one executable scenario.
"""
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "catalog"

UNIVERSE_BATCH1_ROWS = [
    ("docker_events", "docker-events",
     "Docker Engine Events",
     "docker", "Container Platform & DevOps", "hec", "event",
     "Docker Monitoring (monitoringdocker Add-on)"),
    ("bluecoat:proxysg:access:file", "bluecoat-proxysg-access-file",
     "Symantec/Broadcom ProxySG Access Log (file/main format)",
     "broadcom_symantec", "Web Security & Proxy", "syslog", "event",
     "Splunk Add-on for Symantec Blue Coat ProxySG"),
    ("wazuh:alerts", "wazuh-alerts",
     "Wazuh Manager Alerts (alerts.log)",
     "wazuh", "Host IDS & XDR", "syslog", "event",
     "Wazuh Splunk Integration (alerts.log file monitor)"),
    ("nozomi:universal_alert", "nozomi-universal-alert",
     "Nozomi Networks Universal Alert",
     "nozomi_networks", "OT & ICS Security", "syslog", "event",
     "Nozomi Networks Universal Add-on"),
]

TOPOLOGY_ID = "mixed_sase"

SCENARIOS = [
    {
        "id": "ub1_ot_proxy_host_hunt", "code": "SEC-UB1-01",
        "name": "OT Tamper to Container Host Hunt (Universe Batch-1)",
        "display_name": "OT Tamper to Container Host Hunt (Universe Batch-1)",
        "category": "SECURITY", "ecosystem": "mixed_vendor",
        "maturity": "CONTRACTED",
        "description": ("Converged OT/IT hunt: Nozomi Networks OT IDS alerts"
                        " (PLC program change), Symantec/Broadcom ProxySG "
                        "denied exfil attempts, Wazuh manager rootcheck "
                        "alerts and Docker engine container lifecycle events"
                        " - authentic vendor-native RAW with correlation on "
                        "HEC fields only."),
        "attack_vector": "PLC program modification (OT), "
                         "T1048 exfiltration over web proxy, T1564 hidden "
                         "files and directories.",
        "defense_mechanism": "OT threat detection (Nozomi), web proxy "
                             "verdicts (ProxySG), rootcheck host IDS "
                             "(Wazuh), container runtime audit (Docker).",
        "generation_mode": "SCENARIO_DERIVED",
        "sourcetypes": [
            "nozomi:universal_alert", "bluecoat:proxysg:access:file",
            "wazuh:alerts", "docker_events",
        ],
        "default_topology_id": TOPOLOGY_ID,
        "topology_id": TOPOLOGY_ID,
        "difficulty": "ADVANCED", "estimated_duration_sec": 40,
        "vendor_scope": ["nozomi_networks", "broadcom_symantec", "wazuh",
                         "docker"],
        "telemetry_requirements": ["hec_event"],
        "generation_modes": ["SCENARIO_DERIVED"],
        "affected_entities": [TOPOLOGY_ID],
        "expected_observations": [
            "Nozomi OT IDS SIGN:PROGRAM:CHANGE alert",
            "ProxySG OBSERVED baseline category hit",
            "ProxySG TCP_DENIED exfil attempt (DENIED)",
            "Wazuh rootcheck hidden process + hidden file alerts",
            "Docker container/network lifecycle events",
        ],
        "expected_phases": ["baseline", "fault", "propagate", "validate"],
        "use_case": {
            "objective": "universe batch-1 multi-vendor hunt across OT IDS, "
                         "web proxy, host IDS and container runtime RAW",
            "required_telemetry": ["nozomi:universal_alert",
                                   "bluecoat:proxysg:access:file"],
        },
        "phases": [
            {"phase": "BASELINE", "name": "Nominal operations",
             "duration_ticks": 2,
             "description": "Container lifecycle + observed proxy transaction"
                            ".",
             "expected_observations": ["docker_events create",
                                       "proxysg OBSERVED"]},
            {"phase": "FAULT", "name": "OT program tamper",
             "duration_ticks": 1,
             "description": "Nozomi SIGN:PROGRAM:CHANGE alert on PLC edit.",
             "expected_observations": ["nozomi:universal_alert "
                                       "SIGN:PROGRAM:CHANGE"]},
            {"phase": "PROPAGATE", "name": "Exfil attempt + container churn",
             "duration_ticks": 2,
             "description": "Denied ProxySG exfil attempt and container "
                            "network attach.",
             "expected_observations": ["bluecoat:proxysg:access:file "
                                       "TCP_DENIED"]},
            {"phase": "VALIDATE", "name": "Host response + recovery",
             "duration_ticks": 2,
             "description": "Wazuh rootcheck alerts and host investigation.",
             "expected_observations": ["wazuh:alerts rule 521/510"]},
        ],
        "vendor_tech_details": [
            {"vendor": "nozomi_networks", "sourcetype": "nozomi:universal_alert"},
            {"vendor": "broadcom_symantec",
             "sourcetype": "bluecoat:proxysg:access:file"},
            {"vendor": "wazuh", "sourcetype": "wazuh:alerts"},
            {"vendor": "docker", "sourcetype": "docker_events"},
        ],
        "raw_evidence": ("catalog/raw_reference/universe_batch1/ + "
                         "provenance.json (universe:batch1 entries)"),
        "registry_reference": "catalog/universe_batch1.json",
    },
]

UNIVERSE_BATCH1_VENDORS = [
    {
        "id": "docker", "legacy_id": "docker",
        "name": "Docker", "slug": "docker",
        "category": "Container Platform & DevOps",
        "splunk_app_name": "Docker Monitoring (monitoringdocker Add-on)",
        "splunkbase_id": "", "splunkbase_url": "",
        "doc_url": "https://docs.docker.com/engine/reference/commandline/events/",  # noqa
        "supported_device_types": ["web_server"],
        "supported_protocols": ["hec"],
        "header_type": "RFC3339Nano event text",
        "delimiter": " ",
        "timestamp_format": "RFC3339Nano",
        "cim_models": ["Change Analysis"],
        "field_mappings": {},
        "sample_events": [],
        "primary_sourcetypes": ["docker_events"],
    },
    {
        "id": "broadcom_symantec", "legacy_id": "symantec",
        "name": "Symantec (Broadcom), Web & Network Security", "slug": "broadcom_symantec",  # noqa
        "category": "Web Security & Proxy",
        "splunk_app_name": "Splunk Add-on for Symantec Blue Coat ProxySG",
        "splunkbase_id": "2758", "splunkbase_url": "https://splunkbase.splunk.com/app/2758/",
        "doc_url": "https://www.elastic.co/docs/reference/integrations/proxysg",  # noqa
        "supported_device_types": ["sase_proxy"],
        "supported_protocols": ["syslog", "file"],
        "header_type": "Space-delimited positional (main log format)",
        "delimiter": " ",
        "timestamp_format": "YYYY-MM-DD HH:MM:SS",
        "cim_models": ["Web", "Network Traffic"],
        "field_mappings": {},
        "sample_events": [],
        "primary_sourcetypes": ["bluecoat:proxysg:access:file"],
    },
    {
        "id": "wazuh", "legacy_id": "wazuh",
        "name": "Wazuh", "slug": "wazuh",
        "category": "Host IDS & XDR",
        "splunk_app_name": "Wazuh Splunk Integration",
        "splunkbase_id": "", "splunkbase_url": "",
        "doc_url": "https://documentation.wazuh.com/current/user-manual/"  # noqa
                   "capabilities/malware-detection/rootkits-behavior-detection.html",  # noqa
        "supported_device_types": ["web_server"],
        "supported_protocols": ["syslog", "file"],
        "header_type": "Multi-line alert block (** Alert header)",
        "delimiter": "\n",
        "timestamp_format": "2022 Nov 15 09:35:57 (epoch.us header)",
        "cim_models": ["Alerts", "Malware Attacks"],
        "field_mappings": {},
        "sample_events": [],
        "primary_sourcetypes": ["wazuh:alerts"],
    },
    {
        "id": "nozomi_networks", "legacy_id": "nozomi",
        "name": "Nozomi Networks", "slug": "nozomi_networks",
        "category": "OT & ICS Security",
        "splunk_app_name": "Nozomi Networks Universal Add-on",
        "splunkbase_id": "6905", "splunkbase_url": "https://splunkbase.splunk.com/app/6905/",
        "doc_url": "https://www.elastic.co/docs/reference/integrations/nozomi_networks",  # noqa
        "supported_device_types": ["optical_core"],
        "supported_protocols": ["syslog"],
        "header_type": "JSON (vendor-native alert object)",
        "delimiter": "",
        "timestamp_format": "Unix ms",
        "cim_models": ["Alerts", "Incidents"],
        "field_mappings": {},
        "sample_events": [],
        "primary_sourcetypes": ["nozomi:universal_alert"],
    },
]


def slug_id(splunk_sourcetype: str) -> str:
    return splunk_sourcetype.replace(":", "-").lower()


def build_row(row) -> dict:
    (st_name, custom_id, display, vendor, category, protocol, kind,
     required_ta) = row
    return {
        "id": custom_id or slug_id(st_name),
        "splunk_sourcetype": st_name,
        "display_name": display,
        "vendor_id": vendor,
        "category": category,
        "data_kind": kind,
        "default_index": "idx_network_ops",
        "recommended_index": "netops_logs",
        "generation_mode": "STATEFUL",
        "protocol": protocol,
        "sample_file": None,
        "required_ta": required_ta,
        "aliases": [custom_id or slug_id(st_name), st_name],
        "deprecated_aliases": [],
        "is_benchmark_197": False,
        "status": "active",
    }


def main() -> None:
    with open(CATALOG / "sourcetypes.json") as f:
        st_rows = json.load(f)
    existing = {r["splunk_sourcetype"] for r in st_rows}
    added = []
    for row in UNIVERSE_BATCH1_ROWS:
        if row[0] in existing:
            continue
        st_rows.append(build_row(row))
        added.append(row[0])
    with open(CATALOG / "sourcetypes.json", "w") as f:
        json.dump(st_rows, f, indent=1)

    with open(CATALOG / "vendors.json") as f:
        vendors = json.load(f)
    v_ids = {v["id"] for v in vendors}
    vend_added = []
    for v in UNIVERSE_BATCH1_VENDORS:
        if v["id"] in v_ids:
            vendors = [v if row["id"] == v["id"] else row for row in vendors]
            continue
        vendors.append(v)
        vend_added.append(v["id"])
    with open(CATALOG / "vendors.json", "w") as f:
        json.dump(vendors, f, indent=1)

    with open(CATALOG / "scenarios.json") as f:
        scenarios = json.load(f)
    s_ids = {s["id"] for s in scenarios}
    scn_added = []
    for s in SCENARIOS:
        if s["id"] in s_ids:
            scenarios = [s if row["id"] == s["id"] else row for row in scenarios]
            continue
        scenarios.append(s)
        scn_added.append(s["id"])
    with open(CATALOG / "scenarios.json", "w") as f:
        json.dump(scenarios, f, indent=1)

    print("batch1 sourcetype rows added:", len(added), added)
    print("batch1 vendor rows added:", vend_added)
    print("batch1 scenario rows added:", scn_added)
    print("totals: sourcetypes=%d vendors=%d scenarios=%d"
          % (len(st_rows), len(vendors), len(scenarios)))


if __name__ == "__main__":
    main()
