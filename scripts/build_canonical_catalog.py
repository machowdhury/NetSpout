#!/usr/bin/env python3
"""
NetSpout Canonical Catalog Generator
Extracts, merges, and validates metadata from:
- src/netspout_core/vendor_catalog.py (36 vendors, 238 sourcetypes)
- netspout/appserver/static/samples_manifest.json (213 samples, 209 sourcetypes)
- netspout/appserver/static/cisco_catalog.json (34 Cisco sourcetypes)
- frontend/src/presets/defaultTopologies.ts (29 scenarios, 17 topologies)
- src/netspout_core/models.py (17 NodeTypes, 29 ScenarioTypes)
- tests/requested_sourcetypes.csv (197 benchmark sourcetypes)

Outputs to catalog/*.json:
- vendors.json
- sourcetypes.json
- scenarios.json
- device_types.json
- topologies.json
- samples.json
- telemetry_protocols.json
- aliases.json
"""

import os
import sys
import json
import csv
import re
from typing import Dict, List, Any, Set

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

CATALOG_DIR = os.path.join(REPO_ROOT, "catalog")
os.makedirs(CATALOG_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. Load Existing Metadata
# -----------------------------------------------------------------------------
from netspout_core.vendor_catalog import VENDOR_CATALOG
from netspout_core.models import NodeType, ScenarioType, ScenarioContract

with open(os.path.join(REPO_ROOT, "netspout/appserver/static/samples_manifest.json")) as f:
    manifest_data = json.load(f)

with open(os.path.join(REPO_ROOT, "netspout/appserver/static/cisco_catalog.json")) as f:
    cisco_catalog_data = json.load(f)

req_sourcetypes = set()
with open(os.path.join(REPO_ROOT, "tests/requested_sourcetypes.csv")) as f:
    reader = csv.DictReader(f)
    for row in reader:
        st = row.get("sourcetype", "").strip()
        if st:
            req_sourcetypes.add(st)

with open(os.path.join(REPO_ROOT, "frontend/src/presets/defaultTopologies.ts")) as f:
    ts_content = f.read()

# -----------------------------------------------------------------------------
# 2. Build Canonical Vendors
# -----------------------------------------------------------------------------
print(">> 1. Building canonical vendors...")
canonical_vendors = []
vendor_legacy_map = {}
vendor_slug_to_id = {}

for v in VENDOR_CATALOG:
    vid = v.get("vendor_slug") or v["id"].replace("-", "_")
    legacy_id = v["id"]
    vendor_legacy_map[legacy_id] = vid
    vendor_slug_to_id[v.get("vendor_slug", vid)] = vid
    vendor_slug_to_id[legacy_id] = vid

    cat = v.get("category", "")
    dev_types = []
    if "Firewall" in cat or "UTM" in cat:
        dev_types.append("firewall")
    if "Routing" in cat:
        dev_types.append("router")
    if "Switching" in cat or "Fabric" in cat:
        dev_types.append("switch")
    if "ADC" in cat or "Delivery" in cat:
        dev_types.append("load_balancer")
    if "Wireless" in cat:
        dev_types.append("wireless_ap")
    if "SASE" in cat or "SSE" in cat or "CASB" in cat:
        dev_types.append("sase_proxy")
    if "SNMP" in cat:
        dev_types.extend(["router", "switch", "firewall"])
    if not dev_types:
        dev_types.append("switch")

    protocols = ["syslog", "hec"]
    if "sc4snmp" in vid or "cisco" in vid or "arista" in vid or "juniper" in vid:
        protocols.append("snmp")
    if "cisco" in vid or "arista" in vid or "juniper" in vid or "nokia" in vid:
        protocols.append("gnmi")

    vendor_obj = {
        "id": vid,
        "legacy_id": legacy_id,
        "name": v.get("vendor"),
        "slug": v.get("vendor_slug", vid),
        "category": cat,
        "splunk_app_name": v.get("name"),
        "splunkbase_id": v.get("splunkbase_id"),
        "splunkbase_url": v.get("splunkbase_url"),
        "doc_url": v.get("doc_url"),
        "supported_device_types": sorted(list(set(dev_types))),
        "supported_protocols": sorted(list(set(protocols))),
        "header_type": v.get("header_type"),
        "delimiter": v.get("delimiter"),
        "timestamp_format": v.get("timestamp_format"),
        "cim_models": v.get("cim_models", []),
        "field_mappings": v.get("field_mappings", {}),
        "sample_events": v.get("sample_events", {}),
        "primary_sourcetypes": v.get("sourcetypes", [])
    }
    canonical_vendors.append(vendor_obj)

canonical_vendors.sort(key=lambda x: x["id"])

# -----------------------------------------------------------------------------
# 3. Build Canonical Sourcetypes
# -----------------------------------------------------------------------------
print(">> 2. Building canonical sourcetypes...")

manifest_st_info = {}
for cat in manifest_data.get("categories", []):
    cat_name = cat.get("categoryName", "General")
    for s in cat.get("samples", []):
        st = s.get("detectedSourcetype") or s.get("sourcetype")
        if not st:
            continue
        if st not in manifest_st_info:
            manifest_st_info[st] = {
                "category": cat_name,
                "sample_id": s.get("id"),
                "sample_file": s.get("sampleFile") or (s.get("files", [None])[0]),
                "name": s.get("name"),
                "detectedIndex": s.get("detectedIndex", "main"),
                "recommendedIndex": (s.get("ruleEngine") or {}).get("recommendedIndex", "netops_logs"),
                "requiredTA": (s.get("ruleEngine") or {}).get("requiredTA")
            }

def find_vendor_for_sourcetype(st: str) -> str:
    st_lower = st.lower()
    if st_lower.startswith("cisco:sdwan") or "sdwan" in st_lower and "cisco" in st_lower:
        return "cisco_sdwan"
    elif st_lower.startswith("cisco:catalyst"):
        return "cisco_catalyst"
    elif st_lower.startswith("cisco:dnac"):
        return "cisco_catalyst"
    elif st_lower.startswith("cisco:ise"):
        return "cisco_ise"
    elif st_lower.startswith("cisco:duo"):
        return "cisco_duo"
    elif st_lower.startswith("cisco:intersight"):
        return "cisco_intersight"
    elif st_lower.startswith("cisco:dc") or "aci" in st_lower or "nexus" in st_lower:
        return "cisco_aci"
    elif st_lower.startswith("cisco:asa") or st_lower.startswith("cisco:ftd"):
        return "cisco_asa"
    elif st_lower.startswith("cisco:mds"):
        return "cisco_catalyst"
    elif st_lower.startswith("cisco:ios") or st_lower.startswith("cisco:"):
        return "cisco_ios"
    elif st_lower.startswith("meraki"):
        return "cisco_meraki"
    elif st_lower.startswith("pan:") or "palo" in st_lower:
        return "palo_alto"
    elif "forti" in st_lower or st_lower.startswith("fgt"):
        return "fortinet"
    elif "checkpoint" in st_lower:
        return "checkpoint"
    elif "arista" in st_lower:
        return "arista_eos"
    elif "juniper" in st_lower:
        return "juniper_junos"
    elif "nokia" in st_lower:
        return "nokia_sr"
    elif "aruba" in st_lower:
        return "aruba_cx"
    elif "sc4snmp" in st_lower or "snmp" in st_lower:
        return "sc4snmp"
    elif "nutanix" in st_lower:
        return "nutanix"
    elif "zscaler" in st_lower:
        return "zscaler_zia"
    elif "cloudflare" in st_lower:
        return "cloudflare"
    elif "netskope" in st_lower:
        return "netskope"
    elif "radware" in st_lower:
        return "radware"
    elif "f5:" in st_lower:
        return "f5_bigip"
    elif "extrahop" in st_lower:
        return "extrahop"
    elif "netscout" in st_lower:
        return "netscout"
    elif "sophos" in st_lower:
        return "sophos"
    elif "vmware" in st_lower:
        return "vmware_nsx"
    elif "extreme" in st_lower:
        return "extreme_networks"
    elif "huawei" in st_lower:
        return "huawei_vrp"
    elif "dell" in st_lower:
        return "dell_os10"
    elif "watchguard" in st_lower:
        return "watchguard"
    elif "sonicwall" in st_lower:
        return "sonicwall"
    elif "forcepoint" in st_lower:
        return "forcepoint"
    elif "a10" in st_lower:
        return "a10_networks"
    elif "citrix" in st_lower:
        return "citrix_netscaler"
    elif "openconfig" in st_lower:
        return "cisco_ios"
    elif "nginx" in st_lower or "postgresql" in st_lower or "netapp" in st_lower:
        return "splunk"
    elif "kube" in st_lower or "stream" in st_lower or "geo" in st_lower or "http" in st_lower:
        return "splunk"
    return "cisco_ios"

# Include scenario sourcetypes
scenario_sourcetypes = [
    "nginx:plus:kv",
    "postgresql:audit",
    "openconfig:gnmi:telemetry",
    "cisco:ios:mdt",
    "cisco:ise:nac:8021x",
    "cisco:ise:trustsec:sgt",
    "cisco:duo:remote:vpn",
    "cisco:duo:push:prompt",
    "cisco:mds:san:fc",
    "netapp:ontap:nas",
    "pan:ble:iot:sensor",
    "arista:flow:ipfix"
]

all_sourcetype_names = set(req_sourcetypes) | set(scenario_sourcetypes)
for v in VENDOR_CATALOG:
    for st in v.get("sourcetypes", []):
        all_sourcetype_names.add(st)
for st in manifest_st_info.keys():
    all_sourcetype_names.add(st)
for st in cisco_catalog_data.keys():
    all_sourcetype_names.add(st)

canonical_sourcetypes = []
aliases_map = {}

TYPO_ST = "cisco:sdwan:sytem:logs"
CANONICAL_ST = "cisco:sdwan:system:logs"

aliases_map[TYPO_ST] = {
    "canonical_sourcetype": CANONICAL_ST,
    "canonical_id": "cisco-sdwan-system-logs",
    "type": "DEPRECATED_ALIAS",
    "reason": "Typographical error in historical releases (sytem -> system); retained for query and test compatibility."
}
aliases_map["cisco-sdwan-sytem-logs"] = {
    "canonical_sourcetype": CANONICAL_ST,
    "canonical_id": "cisco-sdwan-system-logs",
    "type": "DEPRECATED_ALIAS",
    "reason": "Typographical error in historical sample filenames; retained for backward compatibility."
}

for st in sorted(all_sourcetype_names):
    is_typo = (st == TYPO_ST)
    st_id = re.sub(r'[^a-zA-Z0-9_\-]', '-', st).lower()
    m_info = manifest_st_info.get(st, {})
    vendor_id = find_vendor_for_sourcetype(st)

    data_kind = "metric" if ("metric" in st or "perf" in st or "counters" in st) else "event"
    default_index = "cisco_mdt_metrics" if data_kind == "metric" else "idx_network_ops"
    
    if "metric" in st or "mdt" in st or "telemetry" in st:
        gen_mode = "SYNTHETIC"
    elif m_info.get("sample_file"):
        gen_mode = "REPLAY"
    else:
        gen_mode = "STATEFUL"

    disp_name = m_info.get("name") or st.replace(":", " ").replace("_", " ").title()

    aliases = [st, st_id]
    deprecated_aliases = []
    if st == CANONICAL_ST:
        deprecated_aliases.extend([TYPO_ST, "cisco-sdwan-sytem-logs"])

    st_obj = {
        "id": st_id,
        "splunk_sourcetype": st,
        "display_name": disp_name,
        "vendor_id": vendor_id,
        "category": m_info.get("category", "Enterprise Telemetry"),
        "data_kind": data_kind,
        "default_index": default_index,
        "recommended_index": m_info.get("recommendedIndex", "netops_logs"),
        "generation_mode": gen_mode,
        "protocol": "syslog" if data_kind == "event" else "hec",
        "sample_file": m_info.get("sample_file"),
        "required_ta": m_info.get("requiredTA"),
        "aliases": sorted(list(set(aliases))),
        "deprecated_aliases": deprecated_aliases,
        "is_benchmark_197": (st in req_sourcetypes),
        "status": "deprecated" if is_typo else "active"
    }
    if is_typo:
        st_obj["canonical_sourcetype"] = CANONICAL_ST
        st_obj["canonical_id"] = "cisco-sdwan-system-logs"

    canonical_sourcetypes.append(st_obj)

canonical_sourcetypes.sort(key=lambda x: x["splunk_sourcetype"])

# -----------------------------------------------------------------------------
# 4. Build Canonical Scenarios
# -----------------------------------------------------------------------------
print(">> 3. Building canonical scenarios...")

scen_blocks = re.findall(
    r'\{\s*id:\s*[\'\"](.*?)[\'\"],\s*name:\s*[\'\"](.*?)[\'\"],\s*code:\s*[\'\"](.*?)[\'\"],\s*ecosystem:\s*[\'\"](.*?)[\'\"],\s*description:\s*[\'\"](.*?)[\'\"],\s*attackVector:\s*[\'\"](.*?)[\'\"],\s*defenseMechanism:\s*[\'\"](.*?)[\'\"],\s*sourcetypes:\s*\[(.*?)\]\s*\}',
    ts_content,
    re.DOTALL
)

canonical_scenarios = []
for sid, name, code, eco, desc, attack, defense, st_block in scen_blocks:
    sts = [s.strip("'\" \n") for s in st_block.split(",") if s.strip("'\" \n")]
    
    if "ddos" in sid or "sql" in sid or "lateral" in sid or "breach" in sid:
        cat = "SECURITY"
    elif "sdwan" in sid or "wan" in sid or "vpn" in sid:
        cat = "WAN"
    elif "wlan" in sid or "wireless" in sid or "rogue" in sid:
        cat = "WIRELESS"
    elif "aci" in sid or "san" in sid or "nas" in sid or "optical" in sid:
        cat = "DATACENTER"
    elif "service_provider" in sid or "man" in sid:
        cat = "SERVICE_PROVIDER"
    elif "openconfig" in sid or "mdt" in sid:
        cat = "SERVICE_ASSURANCE"
    else:
        cat = "NETWORK_OPERATIONS"

    # Set default topology ID matching canonical topology presets
    topo_id = sid
    if sid == "cisco_campus_rogue":
        topo_id = "cisco_campus"
    elif sid == "cisco_sdwan_brownout":
        topo_id = "cisco_sdwan"
    elif sid == "cisco_aci_microburst":
        topo_id = "cisco_aci"
    elif sid == "mixed_edge_breach":
        topo_id = "mixed_edge"
    elif sid == "mixed_sase_degradation":
        topo_id = "mixed_sase"
    elif sid == "mixed_backbone_optical":
        topo_id = "mixed_optical"
    elif sid == "normal_traffic":
        topo_id = "secure"
    elif sid == "ddos_attack":
        topo_id = "secure"
    elif sid == "sql_injection":
        topo_id = "bypassed"
    elif sid == "lateral_movement":
        topo_id = "lateral"
    elif sid == "openconfig_mdt_streaming":
        topo_id = "openconfig_core"
    elif sid == "pure_cisco_enterprise":
        topo_id = "pure_cisco_enterprise"
    elif sid == "mixed_vendor_enterprise":
        topo_id = "mixed_vendor_enterprise"
    elif sid == "service_provider_cisco":
        topo_id = "service_provider_cisco"
    elif sid == "service_provider_mixed":
        topo_id = "service_provider_mixed"
    elif sid == "sdwan_connected_core":
        topo_id = "sdwan_connected_core"
    elif sid == "wireless_connected_core_cisco":
        topo_id = "wireless_connected_core_cisco"
    elif sid == "wireless_connected_core_mixed":
        topo_id = "wireless_connected_core_mixed"

    clean_name = re.sub(r'^Mode [A-Z0-9]+:\s*', '', name)
    clean_desc = desc.replace("\\'", "'")
    clean_attack = attack.replace("\\'", "'")
    clean_defense = defense.replace("\\'", "'")

    scen_obj = {
        "id": sid,
        "code": code,
        "name": clean_name,
        "display_name": clean_name,
        "category": cat,
        "ecosystem": eco,
        "description": clean_desc,
        "attack_vector": clean_attack,
        "defense_mechanism": clean_defense,
        "generation_mode": "SCENARIO_DERIVED",
        "sourcetypes": sts,
        "default_topology_id": topo_id,
        "topology_id": topo_id,
        "difficulty": ("BEGINNER" if "normal" in sid else "ADVANCED" if "arch_" in sid or "sp_" in sid else "INTERMEDIATE"),
        "estimated_duration_sec": 30,
        "vendor_scope": ([eco] if eco and eco != "both" else ["cisco", "palo_alto", "juniper"]),
        "telemetry_requirements": ["syslog", "snmp"],
        "generation_modes": ["SCENARIO_DERIVED"],
        "affected_entities": [topo_id],
        "expected_observations": [clean_attack or "Event observed"],
        "expected_phases": [
            "baseline",
            "trigger_event",
            "telemetry_spike",
            "policy_enforcement",
            "steady_state"
        ]
    }

    if sid == "cisco_sdwan_brownout":
        scen_obj["difficulty"] = "INTERMEDIATE"
        scen_obj["vendor_scope"] = ["cisco_sdwan"]
        scen_obj["telemetry_requirements"] = ["syslog", "gnmi", "snmp"]
        scen_obj["affected_entities"] = ["edge-branch-mpls", "vedge-branch-01", "vedge-hub-01"]
        scen_obj["fault_definition"] = {
            "type": "link_degradation",
            "target_edge_id": "edge-branch-mpls",
            "packet_loss_pct": 12.0,
            "latency_ms": 150.0,
            "jitter_ms": 35.0,
            "description": "Simulates 12% packet loss and 150ms latency across primary MPLS transport."
        }
        scen_obj["recovery_definition"] = {
            "type": "link_restoration",
            "target_edge_id": "edge-branch-mpls",
            "description": "Restores primary MPLS circuit to <1% loss and nominal latency."
        }
        scen_obj["phases"] = [
            {"phase": "INITIALIZE", "name": "Topology Provisioning", "duration_ticks": 1, "description": "Initialize SD-WAN branch and hub nodes with dual transport paths.", "expected_observations": ["Nodes active"]},
            {"phase": "BASELINE", "name": "Healthy Path SLA", "duration_ticks": 2, "description": "BFD sessions establish SLA metrics below brownout thresholds.", "expected_observations": ["BFD jitter < 10ms", "0% packet loss"]},
            {"phase": "DEGRADE", "name": "Carrier Brownout Injection", "duration_ticks": 3, "description": "Introduce 12% packet loss and 150ms latency on primary MPLS.", "fault_action": scen_obj["fault_definition"], "expected_observations": ["BFD latency violation detected", "Path quality score drops"]},
            {"phase": "FAILOVER", "name": "App-Route Dynamic Steer", "duration_ticks": 2, "description": "vManage App-Route policy activates; traffic steers to secondary DIA Internet circuit.", "expected_observations": ["cisco:sdwan:approute reroute event", "Secondary tunnel active"]},
            {"phase": "RECOVER", "name": "Carrier Restoration", "duration_ticks": 2, "description": "Restore primary MPLS circuit quality to nominal levels.", "recovery_action": scen_obj["recovery_definition"], "expected_observations": ["BFD alarms cleared", "Traffic returns to primary"]},
            {"phase": "VALIDATE", "name": "SLA Verification", "duration_ticks": 1, "description": "Verify complete recovery and SLA conformance.", "expected_observations": ["All tunnels healthy"]}
        ]
        scen_obj["use_case"] = {
            "objective": "Demonstrate detection, isolation, and automated App-Route failover of an enterprise SD-WAN branch circuit suffering brownout degradation, followed by automated recovery.",
            "required_telemetry": ["cisco:sdwan:bfd", "cisco:sdwan:approute", "cisco:sdwan:linkhealth", "cisco:sdwan:system:logs"],
            "expected_progression": [
                "Healthy baseline traffic over primary MPLS circuit",
                "Carrier brownout introduced with 12% loss and 150ms latency",
                "BFD path quality drops below SLA threshold",
                "App-Route steers critical application traffic to backup DIA tunnel",
                "Primary circuit restored; traffic returns to primary MPLS tunnel"
            ],
            "expected_observations": [
                "BFD degradation alerts in cisco:sdwan:bfd",
                "Tunnel health degradation in cisco:sdwan:linkhealth",
                "AppRoute failover event in cisco:sdwan:approute",
                "Recovery log in cisco:sdwan:system:logs"
            ],
            "validation_criteria": [
                "cisco:sdwan:system:logs emitted with failover confirmation",
                "cisco:sdwan:approute emitted with reroute action",
                "Primary edge state restored to nominal"
            ]
        }
        scen_obj["validation_rules"] = [
            {"id": "sdwan-val-01", "name": "SD-WAN Sourcetypes Present", "type": "COUNT_THRESHOLD", "target_sourcetype": "cisco:sdwan:linkhealth", "min_count": 1, "description": "Verify at least 1 SD-WAN linkhealth log was emitted."},
            {"id": "sdwan-val-02", "name": "AppRoute Failover Action", "type": "EVENT_EXISTS", "target_field": "action", "expected_value": "allowed", "comparison": "in", "description": "Verify AppRoute failover event was generated."},
            {"id": "sdwan-val-03", "name": "Link Health Transition", "type": "STATE_TRANSITION", "target_field": "status", "expected_value": "restored", "comparison": "==", "description": "Verify edge link returned to up/restored status."}
        ]

    elif sid == "cisco_campus_rogue":
        scen_obj["difficulty"] = "INTERMEDIATE"
        scen_obj["vendor_scope"] = ["cisco_catalyst", "cisco_ise"]
        scen_obj["telemetry_requirements"] = ["syslog", "snmp"]
        scen_obj["affected_entities"] = ["cat9300-access01", "wlc-9800-core", "rogue-ap-unauth"]
        scen_obj["phases"] = [
            {"phase": "BASELINE", "name": "Authorized Campus Operations", "duration_ticks": 2, "description": "Normal 802.1X client authentication and authorized AP telemetry.", "expected_observations": ["Normal client associations"]},
            {"phase": "FAULT", "name": "Rogue AP Broadcast Injection", "duration_ticks": 3, "description": "Unapproved rogue access point powers on broadcasting corporate SSID.", "expected_observations": ["Rogue AP beacon frames detected", "Channel conflict"]},
            {"phase": "PROPAGATE", "name": "WLC & Catalyst Center Alerting", "duration_ticks": 2, "description": "Catalyst 9800 WLC flags rogue AP as malicious and notifies Catalyst Center.", "expected_observations": ["Rogue threat alarm generated"]},
            {"phase": "FAILOVER", "name": "Automated Port Quarantine", "duration_ticks": 2, "description": "Switchport connected to rogue AP placed in quarantine VLAN via ISE change of authorization (CoA).", "expected_observations": ["ISE CoA quarantine action"]},
            {"phase": "RECOVER", "name": "Rogue Device Decommission", "duration_ticks": 2, "description": "Rogue device removed; switchport returned to standard VLAN.", "expected_observations": ["Quarantine cleared"]},
            {"phase": "VALIDATE", "name": "Wireless Security Audit", "duration_ticks": 1, "description": "Verify zero uncontained rogues remain active.", "expected_observations": ["Air quality normal"]}
        ]
        scen_obj["use_case"] = {
            "objective": "Demonstrate campus wireless rogue AP detection, automated containment, and switchport quarantine triage.",
            "required_telemetry": ["cisco:catalyst:networkhealth", "cisco:catalyst:rogue:threat:details", "cisco:ise:nac:8021x"],
            "expected_progression": ["Baseline campus operations", "Rogue AP activated", "WLC detects unauthorized BSSID", "Quarantine port via ISE CoA", "Airspace cleared"],
            "expected_observations": ["Rogue threat detail alert in cisco:catalyst:rogue:threat:details", "ISE quarantine event in cisco:ise:nac:8021x"],
            "validation_criteria": ["At least 1 rogue detection event emitted", "Containment action verified in security telemetry"]
        }
        scen_obj["validation_rules"] = [
            {"id": "rogue-val-01", "name": "Rogue Event Emitted", "type": "COUNT_THRESHOLD", "target_sourcetype": "cisco:catalyst:rogue:threat_details", "min_count": 1, "description": "Verify rogue threat detection logged."},
            {"id": "rogue-val-02", "name": "Security Threat Alerted", "type": "EVENT_EXISTS", "target_field": "action", "expected_value": "alerted", "comparison": "in", "description": "Verify alert status emitted."}
        ]

    elif sid == "cisco_aci_microburst":
        scen_obj["difficulty"] = "ADVANCED"
        scen_obj["vendor_scope"] = ["cisco_nexus", "cisco_aci"]
        scen_obj["telemetry_requirements"] = ["gnmi", "syslog"]
        scen_obj["phases"] = [
            {"phase": "BASELINE", "name": "Nominal Fabric Utilization", "duration_ticks": 2, "description": "East-West container traffic flowing across spine-leaf fabric.", "expected_observations": ["Buffer utilization < 20%"]},
            {"phase": "FAULT", "name": "Egress Queue Saturation Spike", "duration_ticks": 3, "description": "Sub-millisecond microburst saturates leaf switch output buffers.", "expected_observations": ["Buffer watermark > 90%", "PFC pause frames sent"]},
            {"phase": "PROPAGATE", "name": "Telemetry Telemetry Burst", "duration_ticks": 2, "description": "Streaming telemetry emits buffer pool congestion notifications.", "expected_observations": ["cisco:aci:health drop events"]},
            {"phase": "RECOVER", "name": "Buffer Drain & Nominal Flow", "duration_ticks": 2, "description": "Bursty traffic subsides; queues drain back to nominal levels.", "expected_observations": ["Buffer watermarks normalize"]},
            {"phase": "VALIDATE", "name": "Fabric Health Clearance", "duration_ticks": 1, "description": "Verify fabric health metric restoration.", "expected_observations": ["Zero active drop alarms"]}
        ]
        scen_obj["use_case"] = {
            "objective": "Demonstrate ACI spine-leaf datacenter fabric microburst detection and buffer congestion observability.",
            "required_telemetry": ["cisco:aci:health", "cisco:nexus:syslog", "cisco:ios:mdt:metric"],
            "expected_progression": ["Nominal fabric flow", "Ingress microburst", "PFC pause frames and buffer alert", "Congestion clearance", "Health restoration"],
            "expected_observations": ["Buffer drop alerts in cisco:aci:health", "Interface metric anomalies in cisco:ios:mdt:metric"],
            "validation_criteria": ["Microburst alert logged", "Buffer recovery confirmed"]
        }
        scen_obj["validation_rules"] = [
            {"id": "aci-val-01", "name": "ACI Health Telemetry Emitted", "type": "COUNT_THRESHOLD", "target_sourcetype": "cisco:aci:health", "min_count": 1, "description": "Verify ACI health records emitted."},
            {"id": "aci-val-02", "name": "Degradation Status Logged", "type": "EVENT_EXISTS", "target_field": "status", "expected_value": "degraded", "comparison": "in", "description": "Verify congestion state recorded."}
        ]

    elif sid in ("mixed_vendor_enterprise", "mixed_edge_breach"):
        scen_obj["difficulty"] = "INTERMEDIATE"
        scen_obj["vendor_scope"] = ["palo_alto", "fortinet", "cisco_asa", "arista_eos", "juniper_junos"]
        scen_obj["telemetry_requirements"] = ["syslog", "hec"]
        scen_obj["phases"] = [
            {"phase": "BASELINE", "name": "Permitted Perimeter Traffic", "duration_ticks": 2, "description": "Standard HTTP/HTTPS corporate web traffic passing through perimeter firewall.", "expected_observations": ["PAN-OS allow logs", "FortiGate permit logs"]},
            {"phase": "FAULT", "name": "External Exploit Scan Injection", "duration_ticks": 3, "description": "Adversary probes perimeter with OWASP exploit payloads and vulnerability scanning.", "expected_observations": ["Threat signatures triggered"]},
            {"phase": "PROPAGATE", "name": "Cross-Firewall Alert Correlation", "duration_ticks": 2, "description": "Perimeter firewalls drop malicious packets and generate threat alerts.", "expected_observations": ["pan:threat drop events", "fortinet:fortigate:utm alerts"]},
            {"phase": "RECOVER", "name": "Threat Mitigation & Source Ban", "duration_ticks": 2, "description": "Attacker source IP automatically quarantined on edge perimeter.", "expected_observations": ["Drop count returns to nominal"]},
            {"phase": "VALIDATE", "name": "Security Posture Verification", "duration_ticks": 1, "description": "Verify perimeter defense integrity.", "expected_observations": ["Perimeter secure"]}
        ]
        scen_obj["use_case"] = {
            "objective": "Demonstrate unified multi-vendor security correlation across Palo Alto, Fortinet, and Cisco firewalls during an external intrusion attempt.",
            "required_telemetry": ["pan:threat", "pan:traffic", "fortinet:fortigate:utm", "cisco:asa"],
            "expected_progression": ["Baseline traffic allowed", "Exploit scan launched", "Threat detected and dropped by perimeter", "Source IP banned", "Security baseline restored"],
            "expected_observations": ["Threat drop events in pan:threat", "Security events in fortinet:fortigate:utm"],
            "validation_criteria": ["At least 1 threat event generated", "Action blocked or dropped recorded"]
        }
        scen_obj["validation_rules"] = [
            {"id": "mixed-val-01", "name": "Firewall Threat Event Present", "type": "COUNT_THRESHOLD", "target_sourcetype": "pan:threat", "min_count": 1, "description": "Verify PAN threat events logged."},
            {"id": "mixed-val-02", "name": "Threat Packet Dropped", "type": "EVENT_EXISTS", "target_field": "action", "expected_value": "dropped", "comparison": "in", "description": "Verify dropped action in security log."}
        ]

    elif sid == "openconfig_mdt_streaming":
        scen_obj["difficulty"] = "INTERMEDIATE"
        scen_obj["vendor_scope"] = ["openconfig", "cisco", "arista"]
        scen_obj["telemetry_requirements"] = ["gnmi", "hec"]
        scen_obj["phases"] = [
            {"phase": "BASELINE", "name": "MDT Subscription Established", "duration_ticks": 2, "description": "Establish gNMI ON_CHANGE and SAMPLE subscriptions for interface counters.", "expected_observations": ["YANG tree synchronized"]},
            {"phase": "FAULT", "name": "Traffic Step Change", "duration_ticks": 3, "description": "Simulate 500% traffic increase across core transit interfaces.", "expected_observations": ["Interface in-octets jump", "Bandwidth utilization spike"]},
            {"phase": "PROPAGATE", "name": "Streaming MDT Notifications", "duration_ticks": 2, "description": "RFC 7951 JSON-IETF telemetry messages dispatched to Splunk HEC metrics index.", "expected_observations": ["Metric events indexed in cisco_mdt_metrics"]},
            {"phase": "RECOVER", "name": "Traffic Equilibrium", "duration_ticks": 2, "description": "Flow rate settles back to normal baseline levels.", "expected_observations": ["Octet rates normalize"]},
            {"phase": "VALIDATE", "name": "Schema & Counter Verification", "duration_ticks": 1, "description": "Verify monotonic counter integrity and RFC 7951 compliance.", "expected_observations": ["YANG validation clean"]}
        ]
        scen_obj["use_case"] = {
            "objective": "Demonstrate OpenConfig gNMI Model-Driven Telemetry streaming and RFC 7951 JSON-IETF metric ingestion into Splunk metric indexes.",
            "required_telemetry": ["cisco:ios:mdt:metric", "openconfig:gnmi:telemetry"],
            "expected_progression": ["MDT subscription initial sync", "Traffic step increase", "Streaming metric dispatch", "Counter normalization", "Validation"],
            "expected_observations": ["Metric points in cisco:ios:mdt:metric", "RFC 7951 JSON structure"],
            "validation_criteria": ["At least 1 MDT metric record emitted", "Metric values non-zero"]
        }
        scen_obj["validation_rules"] = [
            {"id": "oc-val-01", "name": "MDT Metric Streamed", "type": "COUNT_THRESHOLD", "target_sourcetype": "cisco:ios:mdt:metric", "min_count": 1, "description": "Verify MDT telemetry records emitted."},
            {"id": "oc-val-02", "name": "Action Allowed Recorded", "type": "EVENT_EXISTS", "target_field": "action", "expected_value": "allowed", "comparison": "==", "description": "Verify telemetry transport success."}
        ]

    elif sid in ("ddos_attack", "sql_injection", "lateral_movement", "normal_traffic"):
        scen_obj["difficulty"] = "BEGINNER" if sid == "normal_traffic" else "INTERMEDIATE"
        scen_obj["phases"] = [
            {"phase": "BASELINE", "name": "Baseline Ingress", "duration_ticks": 2, "description": "Normal application traffic.", "expected_observations": ["HTTP permit"]},
            {"phase": "FAULT", "name": "Security Anomaly", "duration_ticks": 3, "description": f"Trigger {sid} security event.", "expected_observations": ["Security event triggered"]},
            {"phase": "PROPAGATE", "name": "Firewall Defense Action", "duration_ticks": 2, "description": "Perimeter defenses mitigate threat.", "expected_observations": ["Drop or block action"]},
            {"phase": "RECOVER", "name": "Mitigation Clearance", "duration_ticks": 2, "description": "Traffic returns to normal baseline.", "expected_observations": ["Nominal operations"]},
            {"phase": "VALIDATE", "name": "Security Audit Check", "duration_ticks": 1, "description": "Verify zero residual anomalies.", "expected_observations": ["Clean security posture"]}
        ]
        scen_obj["use_case"] = {
            "objective": f"Demonstrate network security monitoring and defense triage for {sid}.",
            "required_telemetry": scen_obj.get("sourcetypes", []),
            "expected_progression": ["Baseline", f"{sid} injected", "Defenses trigger", "Recovery", "Audit"],
            "expected_observations": [f"{sid} events in security logs"],
            "validation_criteria": ["Telemetry emitted", "Security mitigation logged"]
        }
        scen_obj["validation_rules"] = [
            {"id": f"{sid}-val-01", "name": "Security Telemetry Present", "type": "COUNT_THRESHOLD", "target_sourcetype": scen_obj.get("sourcetypes", ["pan:threat"])[0] if scen_obj.get("sourcetypes") else None, "min_count": 1, "description": "Verify security logs generated."}
        ]

    else:
        # Default structured contract for remaining 17 architecture & specialized scenarios
        scen_obj["phases"] = [
            {"phase": "BASELINE", "name": "Baseline Steady State", "duration_ticks": 2, "description": f"Establish baseline telemetry for {clean_name}.", "expected_observations": ["Nominal operations"]},
            {"phase": "FAULT", "name": "Fault Trigger Event", "duration_ticks": 3, "description": clean_attack or "Fault injected.", "expected_observations": ["Anomaly detected"]},
            {"phase": "PROPAGATE", "name": "Telemetry & Alert Propagation", "duration_ticks": 2, "description": "Alerts cascade across affected network nodes.", "expected_observations": ["Alerts logged"]},
            {"phase": "FAILOVER", "name": "Policy Mitigation / Failover", "duration_ticks": 2, "description": clean_defense or "Policy enforced.", "expected_observations": ["Failover / mitigation active"]},
            {"phase": "RECOVER", "name": "Steady State Restoration", "duration_ticks": 2, "description": "Return to nominal operational state.", "expected_observations": ["Normal telemetry restored"]},
            {"phase": "VALIDATE", "name": "SLA Verification", "duration_ticks": 1, "description": "Verify health criteria.", "expected_observations": ["SLA met"]}
        ]
        scen_obj["use_case"] = {
            "objective": f"Prove operational resilience and telemetry assurance for {clean_name}.",
            "required_telemetry": scen_obj.get("sourcetypes", []),
            "expected_progression": [p["description"] for p in scen_obj["phases"]],
            "expected_observations": scen_obj["expected_observations"],
            "validation_criteria": [
                f"Required sourcetypes ({len(scen_obj.get('sourcetypes', []))}) emitted and indexed",
                f"Fault trigger signature detected for {sid}",
                "State restored to nominal baseline"
            ]
        }
        scen_obj["validation_rules"] = [
            {"id": f"{sid}-val-01", "name": "Required Telemetry Emitted", "type": "COUNT_THRESHOLD", "target_sourcetype": scen_obj.get("sourcetypes", ["cisco:ios:syslog"])[0] if scen_obj.get("sourcetypes") else None, "min_count": 1, "description": "Verify scenario telemetry is generated."}
        ]

    # Validate against ScenarioContract schema
    ScenarioContract(**scen_obj)
    canonical_scenarios.append(scen_obj)

canonical_scenarios.sort(key=lambda x: x["id"])

# -----------------------------------------------------------------------------
# 5. Build Canonical Device Types
# -----------------------------------------------------------------------------
print(">> 4. Building canonical device types...")

DEVICE_TYPE_SPECS = [
    ("firewall", "Next-Gen Firewall", "security", "Stateful packet inspection, ACL enforcement, NAT, IPS/IDS"),
    ("router", "Edge/Core Router", "network", "BGP/OSPF dynamic routing, MPLS/SRv6, WAN edge termination"),
    ("switch", "L2/L3 Switch", "network", "Ethernet switching, VLANs, 802.1Q trunking, STP/RSTP/MSTP"),
    ("load_balancer", "Application Delivery Controller", "network", "TCP/HTTP server load balancing, SSL termination, health checking"),
    ("subnet", "Network Subnet", "network", "IP broadcast domain segment and CIDR boundary"),
    ("web_server", "Web Application Server", "compute", "HTTP/HTTPS service, Nginx/Apache, API reverse proxy"),
    ("database", "Database Server", "compute", "Relational/NoSQL datastore (PostgreSQL/MySQL), SQL queries"),
    ("client_external", "External Client", "compute", "External Internet client generating inbound HTTP traffic"),
    ("wireless_ap", "Wireless Access Point", "wireless", "Wi-Fi 6/6E/7 access point broadcasting SSIDs and tracking SNR"),
    ("sase_proxy", "Cloud SASE / SSE Proxy", "cloud", "Secure web gateway, CASB proxy, cloud zero trust edge"),
    ("optical_core", "Optical Core Transponder", "network", "DWDM optical wavelength transponder and BER performance"),
    ("storage_san", "Storage Area Network Director", "storage", "Fibre Channel (FC) storage fabric and credit buffers"),
    ("storage_nas", "Network-Attached Storage", "storage", "NFS/SMB shared file storage cluster and IOPS burst"),
    ("vpn_gateway", "VPN Concentrator", "security", "IPsec site-to-site tunnels and remote access client sessions"),
    ("cloud_transit", "Multi-Cloud Transit Gateway", "cloud", "Cloud interconnect (AWS DirectConnect, Azure ExpressRoute)"),
    ("iot_sensor", "IoT Sensor Endpoint", "iot", "Telemetry sensor sending intermittent SCADA/MQTT signals"),
    ("wlc_controller", "Wireless LAN Controller", "wireless", "Centralized AP configuration, RF management, and CAPWAP tunnel")
]

canonical_device_types = []
for dt_id, dt_name, dt_cat, dt_desc in DEVICE_TYPE_SPECS:
    canonical_device_types.append({
        "id": dt_id,
        "name": dt_name,
        "category": dt_cat,
        "description": dt_desc,
        "supported_protocols": ["syslog", "snmp", "hec"]
    })

canonical_device_types.sort(key=lambda x: x["id"])

# -----------------------------------------------------------------------------
# 6. Build Canonical Topologies (all 23 topologies)
# -----------------------------------------------------------------------------
print(">> 5. Building canonical topologies...")

TOPOLOGY_SPECS = [
    # Core Presets
    ("secure", "Protected 3-Tier Enterprise Network (Inline Firewall)", "both", 6, 6, "Standard enterprise DMZ with inline perimeter firewall."),
    ("bypassed", "Bypassed Firewall (Shadow IT / Direct Wire)", "mixed_vendor", 6, 6, "Perimeter firewall bypassed by direct uninspected bypass connection."),
    ("lateral", "Flat Unsegmented Subnet (Ransomware Lateral Spread)", "mixed_vendor", 6, 6, "Unsegmented flat network exposing database to direct peer attacks."),
    ("cisco_campus", "Cisco Campus Core Rogue AP & ISE Quarantine", "pure_cisco", 6, 6, "Campus fabric with Catalyst 9300/9800 and ISE 802.1X quarantine."),
    ("cisco_sdwan", "Cisco SD-WAN WAN Circuit Brownout & BGP Failover", "pure_cisco", 6, 6, "Enterprise dual-link WAN circuit with MPLS and LTE failover."),
    ("cisco_aci", "Cisco Data Center ACI Ingress Microburst", "pure_cisco", 6, 6, "Spine-leaf DC fabric with Nexus 9K switches undergoing burst ingress."),
    ("mixed_edge", "Mixed-Vendor Edge Breach (Meraki -> Catalyst -> Palo Alto)", "mixed_vendor", 6, 6, "Multi-vendor perimeter passing traffic through Palo Alto and Fortinet."),
    ("mixed_sase", "SASE Cloud Ingress Degradation (Zscaler -> Palo Alto -> Nexus)", "mixed_vendor", 6, 6, "Cloud SSE edge routed into on-prem datacenter infrastructure."),
    ("mixed_optical", "Multicast/MPLS Backbone Optical Shift (Nokia -> Juniper -> Arista)", "mixed_vendor", 6, 6, "Carrier optical DWDM backbone connecting metro rings."),
    ("openconfig_core", "OpenConfig Carrier Core & gNMI Assurance", "both", 6, 6, "Carrier backbone streaming real-time OpenConfig YANG MDT."),
    # 11 Architecture Topologies
    ("arch_pan_iot_mesh", "PAN: Personal Area Network - IoT Mesh & BLE Beacon Infrastructure", "both", 6, 6, "Industrial IoT mesh network reporting sensor states."),
    ("arch_lan_campus_access", "LAN: Local Area Network - Campus Access & 802.1X TrustSec", "both", 6, 6, "Enterprise LAN access switching with port-security."),
    ("arch_wlan_meraki_catalyst", "WLAN: Wireless Local Area Network - Catalyst 9800 & Meraki Wi-Fi 6E/7", "both", 6, 6, "High-density campus wireless with CleanAir tracking."),
    ("arch_can_multi_building", "CAN: Campus Area Network - Multi-Building Backbone & Catalyst Center", "pure_cisco", 8, 8, "Multi-building campus network with redundant Catalyst 9600 cores."),
    ("arch_man_carrier_ring", "MAN: Metropolitan Area Network - 100G Carrier Ethernet Ring & G.8032 ERPS", "mixed_vendor", 6, 6, "Metro optical ring spanning 4 data centers with G.8032 sub-50ms failover."),
    ("arch_wan_global_backbone", "WAN: Wide Area Network - Global BGP/MPLS L3VPN Backbone & Optical DWDM", "both", 8, 8, "Inter-continental enterprise WAN with BGP EVPN and segment routing SRv6."),
    ("arch_san_fibre_channel", "SAN: Storage Area Network - Cisco MDS 9700 Fibre Channel & NVMe-oF", "both", 6, 6, "Enterprise storage SAN fabric with FC buffer credits."),
    ("arch_nas_storage_cluster", "NAS: Network-Attached Storage - NetApp ONTAP & PowerScale Clusters", "both", 6, 6, "NFS and SMB storage clusters under IOPS load."),
    ("arch_vpn_remote_workforce", "VPN: Virtual Private Network - Cisco AnyConnect & Site-to-Site IPsec", "both", 6, 6, "Remote workforce VPN endpoint with Duo MFA prompts."),
    ("arch_epn_isolated_intranet", "EPN: Enterprise Private Network - Isolated Corporate Intranet & Multi-Cloud VPC", "both", 6, 6, "Private multi-tenant enterprise intranet connecting branches and VPCs."),
    ("arch_gan_subsea_cloud", "GAN: Global Area Network - Worldwide Multi-Cloud & Subsea Cable Transit", "both", 8, 8, "Trans-continental global network connecting cloud landing stations."),
    # Unified Architecture Presets
    ("pure_cisco_enterprise", "Pure Cisco Enterprise Fabric (Catalyst 9600, 9500, 9300, 9800, ISE, DNA-C)", "pure_cisco", 8, 8, "End-to-end all-Cisco enterprise architecture."),
    ("mixed_vendor_enterprise", "Unified Mixed-Vendor Enterprise Fabric", "mixed_vendor", 8, 8, "Multi-vendor enterprise fabric connecting campus, DC, and SASE cloud."),
    ("service_provider_cisco", "Service Provider Cisco IP/MPLS Backbone", "pure_cisco", 8, 8, "Tier-1 Service Provider backbone with Cisco 8000 and ASR 9000 routers."),
    ("service_provider_mixed", "Service Provider Multi-Vendor Core Transit", "mixed_vendor", 8, 8, "Multi-vendor transit fabric linking Cisco, Juniper, and Nokia edge."),
    ("sdwan_connected_core", "SD-WAN Overlay with Integrated Catalyst Campus Core", "pure_cisco", 8, 8, "Unified SD-WAN edge directly interconnecting with campus distribution."),
    ("wireless_connected_core_cisco", "Catalyst Wireless LAN Fabric with 9800 WLC Integration", "pure_cisco", 6, 6, "Campus wireless fabric mapped to Catalyst core."),
    ("wireless_connected_core_mixed", "Multi-Vendor Campus Wireless & Security Perimeter", "mixed_vendor", 6, 6, "Meraki wireless access points routed through Palo Alto perimeter.")
]

canonical_topologies = []
for tid, tname, teco, tnodes, tedges, tdesc in TOPOLOGY_SPECS:
    canonical_topologies.append({
        "id": tid,
        "name": tname,
        "ecosystem": teco,
        "node_count": tnodes,
        "edge_count": tedges,
        "description": tdesc,
        "associated_scenarios": [s["id"] for s in canonical_scenarios if s.get("default_topology_id") == tid]
    })

canonical_topologies.sort(key=lambda x: x["id"])

# -----------------------------------------------------------------------------
# 7. Build Canonical Samples
# -----------------------------------------------------------------------------
print(">> 6. Building canonical samples...")
canonical_samples = []

seen_sample_ids = set()
for cat in manifest_data.get("categories", []):
    cat_name = cat.get("categoryName")
    for s in cat.get("samples", []):
        sid = s.get("id")
        fn = s.get("sampleFile") or (s.get("files", [None])[0])
        st = s.get("detectedSourcetype") or s.get("sourcetype")

        if sid in seen_sample_ids:
            if sid == "nutanixpc-syslog":
                if st == "nutanixpc_syslog":
                    sid = "nutanixpc-syslog-legacy"
                else:
                    sid = "nutanixpc-syslog-colon"
            elif sid == "nutanixpc-vms":
                if st == "nutanixpc_vms":
                    sid = "nutanixpc-vms-legacy"
                else:
                    sid = "nutanixpc-vms-colon"
            else:
                sid = f"{sid}-dup"

        seen_sample_ids.add(sid)
        is_deprecated = (sid == "cisco-sdwan-sytem-logs" or "-legacy" in sid)

        sample_obj = {
            "id": sid,
            "sample_file": fn,
            "sample_path": f"netspout/appserver/static/samples/{sid}/{fn}" if fn else None,
            "sourcetype": st,
            "vendor_id": find_vendor_for_sourcetype(st) if st else "cisco_ios",
            "category": cat_name,
            "generation_mode": "REPLAY",
            "is_deprecated": is_deprecated
        }
        canonical_samples.append(sample_obj)

canonical_samples.sort(key=lambda x: x["id"])

# -----------------------------------------------------------------------------
# 8. Build Canonical Telemetry Protocols
# -----------------------------------------------------------------------------
print(">> 7. Building canonical telemetry protocols...")
canonical_protocols = [
    {
        "id": "syslog_rfc5424",
        "name": "Syslog RFC 5424",
        "transport": "UDP/TCP",
        "default_port": 514,
        "format": "PRI VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG",
        "generation_mode": "SYNTHETIC",
        "sourcetypes": ["cisco:ios:syslog", "pan:system", "juniper:junos"]
    },
    {
        "id": "syslog_rfc3164",
        "name": "Syslog BSD RFC 3164",
        "transport": "UDP",
        "default_port": 514,
        "format": "<PRI>TIMESTAMP HOSTNAME TAG: MSG",
        "generation_mode": "SYNTHETIC",
        "sourcetypes": ["cisco:asa", "fortigate_traffic"]
    },
    {
        "id": "hec_event",
        "name": "Splunk HTTP Event Collector (Events)",
        "transport": "HTTP/HTTPS",
        "default_port": 8888,
        "format": "JSON {\"time\": ts, \"event\": {...}, \"sourcetype\": ..., \"index\": ...}",
        "generation_mode": "SYNTHETIC",
        "sourcetypes": ["cisco:catalyst:security:events", "cisco:ise:syslog"]
    },
    {
        "id": "hec_metric",
        "name": "Splunk HTTP Event Collector (Metrics)",
        "transport": "HTTP/HTTPS",
        "default_port": 8888,
        "format": "JSON {\"time\": ts, \"event\": \"metric\", \"fields\": {\"metric_name:...\": val}}",
        "generation_mode": "SYNTHETIC",
        "sourcetypes": ["sc4snmp:metric", "cisco_mdt_metrics"]
    },
    {
        "id": "snmp_sc4snmp",
        "name": "SC4SNMP MIB Polling & Trap Gateway",
        "transport": "UDP",
        "default_port": 162,
        "format": "SNMP Trap PDU & SC4SNMP HEC Metric Payload",
        "generation_mode": "SYNTHETIC",
        "sourcetypes": ["sc4snmp:metric", "sc4snmp:event"]
    },
    {
        "id": "gnmi_openconfig",
        "name": "OpenConfig gNMI Model-Driven Telemetry",
        "transport": "gRPC / HTTP",
        "default_port": 57400,
        "format": "RFC 7951 JSON-IETF Hierarchical Telemetry Tree",
        "generation_mode": "STATEFUL",
        "sourcetypes": ["openconfig:gnmi:telemetry", "cisco:ios:mdt:metric"]
    },
    {
        "id": "otlp_http",
        "name": "OpenTelemetry OTLP HTTP Pipeline",
        "transport": "HTTP/HTTPS",
        "default_port": 4318,
        "format": "OTLP JSON Metrics & Logs",
        "generation_mode": "SYNTHETIC",
        "sourcetypes": ["otel:metric", "otel:log"]
    },
    {
        "id": "telegraf_influx",
        "name": "Telegraf Agent HTTP Influx Pipeline",
        "transport": "HTTP",
        "default_port": 8080,
        "format": "Influx Line Protocol or JSON metrics",
        "generation_mode": "SYNTHETIC",
        "sourcetypes": ["telegraf:metric"]
    }
]

# -----------------------------------------------------------------------------
# 9. Build Canonical Aliases
# -----------------------------------------------------------------------------
print(">> 8. Building canonical aliases map...")
for legacy_id, canonical_id in vendor_legacy_map.items():
    if legacy_id != canonical_id:
        aliases_map[legacy_id] = {
            "canonical_id": canonical_id,
            "type": "VENDOR_ALIAS",
            "reason": "Legacy vendor slug used in historical releases."
        }

aliases_map["cisco_campus_rogue"] = {
    "canonical_id": "cisco_campus",
    "type": "TOPOLOGY_ALIAS",
    "reason": "Scenario name alias mapping to cisco_campus topology."
}
aliases_map["cisco_sdwan_brownout"] = {
    "canonical_id": "cisco_sdwan",
    "type": "TOPOLOGY_ALIAS",
    "reason": "Scenario name alias mapping to cisco_sdwan topology."
}
aliases_map["cisco_aci_microburst"] = {
    "canonical_id": "cisco_aci",
    "type": "TOPOLOGY_ALIAS",
    "reason": "Scenario name alias mapping to cisco_aci topology."
}
aliases_map["nutanixpc_syslog"] = {
    "canonical_sourcetype": "nutanixpc:syslog",
    "canonical_id": "nutanixpc-syslog",
    "type": "COMPATIBILITY_ALIAS",
    "reason": "Legacy underscore delimited sourcetype mapped to colon standard."
}
aliases_map["nutanixpc_vms"] = {
    "canonical_sourcetype": "nutanixpc:vms",
    "canonical_id": "nutanixpc-vms",
    "type": "COMPATIBILITY_ALIAS",
    "reason": "Legacy underscore delimited sourcetype mapped to colon standard."
}

# -----------------------------------------------------------------------------
# 10. Write Out Catalog JSON Files
# -----------------------------------------------------------------------------
print(">> 9. Writing catalog JSON files to catalog/...")

files_to_write = {
    "vendors.json": canonical_vendors,
    "sourcetypes.json": canonical_sourcetypes,
    "scenarios.json": canonical_scenarios,
    "device_types.json": canonical_device_types,
    "topologies.json": canonical_topologies,
    "samples.json": canonical_samples,
    "telemetry_protocols.json": canonical_protocols,
    "aliases.json": aliases_map
}

for filename, data in files_to_write.items():
    p = os.path.join(CATALOG_DIR, filename)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  [CREATED] catalog/{filename} ({len(data)} entries, {os.path.getsize(p):,} bytes)")

print("\n✅ Canonical Catalog generation complete!")
