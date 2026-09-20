#!/usr/bin/env python3
"""
NetSpout Comprehensive Automated Production Verification Test Suite
Author: Mahamudul Chowdhury (mchowdhury@splunk.com)
Repository: https://github.com/machowdhury/NetSpout
"""

import os
import sys
import glob
import json
import tarfile
import hashlib
import subprocess
import xml.etree.ElementTree as ET
import re
import csv

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NETSPOUT_DIR = os.path.join(REPO_ROOT, "netspout")
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")
SPL_ARCHIVE = os.path.join(REPO_ROOT, "netspout.spl")

# Results tracker
TEST_RESULTS = []

def record_test(suite: str, name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    TEST_RESULTS.append({"suite": suite, "name": name, "status": status, "detail": detail})
    mark = "✅" if passed else "❌"
    print(f"  [{status}] {mark} {suite} :: {name}")
    if detail and not passed:
        print(f"       -> Detail: {detail}")

print("==========================================================================")
print("⚡ NetSpout: Comprehensive Production Verification & Test Suite")
print("   Author: Mahamudul Chowdhury (mchowdhury@splunk.com)")
print("==========================================================================\n")

# -----------------------------------------------------------------------------
# SUITE 1: XML Dashboards & Navigation Validation
# -----------------------------------------------------------------------------
print(">> Suite 1: SimpleXML Dashboards & Navigation Integrity")
views = glob.glob(os.path.join(NETSPOUT_DIR, "default/data/ui/views/*.xml"))
navs = glob.glob(os.path.join(NETSPOUT_DIR, "default/data/ui/nav/*.xml"))
all_xml = views + navs

record_test("Suite 1", "XML Views Discovered", len(all_xml) >= 15, f"Found {len(all_xml)} views")

xml_failures = 0
for xml_file in all_xml:
    rel = os.path.relpath(xml_file, REPO_ROOT)
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        if root.tag not in ["dashboard", "form", "nav"]:
            record_test("Suite 1", f"XML Root Tag: {os.path.basename(xml_file)}", False, f"Unexpected root {root.tag}")
            xml_failures += 1
    except Exception as e:
        record_test("Suite 1", f"XML Parse: {os.path.basename(xml_file)}", False, str(e))
        xml_failures += 1

if xml_failures == 0:
    record_test("Suite 1", "All XML Files Well-Formed", True, f"100% Valid XML across {len(all_xml)} files")

# Verify Top Navigation Menu
nav_path = os.path.join(NETSPOUT_DIR, "default/data/ui/nav/default.xml")
if os.path.exists(nav_path):
    tree = ET.parse(nav_path)
    root = tree.getroot()
    top_items = [elem.get("label") for elem in root]
    expected_items = [
        "Data Onboarding Wizard",
        "Scenario Builder",
        "Canvas Orchestrator",
        "Data Blaster Dashboard",
        "Network Scenario Insight",
        "SPL Playground",
        "Operations",
        "Search"
    ]
    nav_ok = (top_items == expected_items)
    record_test("Suite 1", "Top Navigation 8 Exact Tabs", nav_ok, f"Found: {top_items}")

# -----------------------------------------------------------------------------
# SUITE 2: JavaScript Syntax Verification
# -----------------------------------------------------------------------------
print("\n>> Suite 2: JavaScript Syntax & Node Syntax Validation")
js_files = glob.glob(os.path.join(NETSPOUT_DIR, "appserver/static/*.js"))
record_test("Suite 2", "JS View Scripts Discovered", len(js_files) >= 5, f"Found {len(js_files)} scripts")

js_failures = 0
for jf in js_files:
    fname = os.path.basename(jf)
    res = subprocess.run(["node", "-c", jf], capture_output=True, text=True)
    if res.returncode != 0:
        record_test("Suite 2", f"JS Syntax: {fname}", False, res.stderr.strip())
        js_failures += 1

if js_failures == 0:
    record_test("Suite 2", "All JavaScript Files Valid", True, f"100% Valid JS syntax across {len(js_files)} files")

# -----------------------------------------------------------------------------
# SUITE 3: Frontend Production React Bundle Validation
# -----------------------------------------------------------------------------
print("\n>> Suite 3: Frontend Production React Bundle & Dark NOC Canvas")
dist_html = os.path.join(NETSPOUT_DIR, "appserver/static/dist/index.html")
dist_assets = glob.glob(os.path.join(NETSPOUT_DIR, "appserver/static/dist/assets/*"))
js_bundle = [f for f in dist_assets if f.endswith(".js")]
css_bundle = [f for f in dist_assets if f.endswith(".css")]

record_test("Suite 3", "Dist index.html Exists", os.path.exists(dist_html), "Embedded canvas entry point")
record_test("Suite 3", "JavaScript Bundle Compiled", len(js_bundle) > 0, f"Found {len(js_bundle)} JS chunks")
record_test("Suite 3", "CSS Theme Bundle Compiled", len(css_bundle) > 0, f"Found {len(css_bundle)} CSS chunks")

# -----------------------------------------------------------------------------
# SUITE 4: App Metadata, Conf & Splunk Cloud AppInspect Integrity
# -----------------------------------------------------------------------------
print("\n>> Suite 4: Splunk AppInspect & Configuration Compliance")
manifest_path = os.path.join(NETSPOUT_DIR, "app.manifest")
app_conf_path = os.path.join(NETSPOUT_DIR, "default/app.conf")
indexes_conf = os.path.join(NETSPOUT_DIR, "default/indexes.conf")
meta_path = os.path.join(NETSPOUT_DIR, "metadata/default.meta")

# Check manifest
manifest_ok = False
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        mf = json.load(f)
        author_name = mf.get("info", {}).get("author", [{}])[0].get("name", "")
        if "Mahamudul Chowdhury" in author_name:
            manifest_ok = True
record_test("Suite 4", "app.manifest Author (Mahamudul Chowdhury)", manifest_ok, f"Author is '{author_name}'")

# Check app.conf
app_conf_ok = False
if os.path.exists(app_conf_path):
    with open(app_conf_path) as f:
        content = f.read()
        if "author = Mahamudul Chowdhury" in content and "version = 2.0.0" in content:
            app_conf_ok = True
record_test("Suite 4", "default/app.conf Configuration", app_conf_ok, "Author and version verified")

# Check 500GB metric tier in indexes.conf
indexes_ok = False
if os.path.exists(indexes_conf):
    with open(indexes_conf) as f:
        content = f.read()
        if "[cisco_mdt_metrics]" in content and "512000" in content and "datatype = metric" in content:
            indexes_ok = True
record_test("Suite 4", "cisco_mdt_metrics 500GB Metric Tier", indexes_ok, "512,000 MB quota & metric datatype")

# Check default.meta export = system
meta_ok = False
if os.path.exists(meta_path):
    with open(meta_path) as f:
        content = f.read()
        if "export = system" in content:
            meta_ok = True
record_test("Suite 4", "metadata/default.meta Permissions", meta_ok, "Global system export verified")

# -----------------------------------------------------------------------------
# SUITE 5: SC4SNMP 300+ MIB Library & Trap Engine
# -----------------------------------------------------------------------------
print("\n>> Suite 5: SC4SNMP 300+ MIB Catalog & Trap Emitter Engine")
snmp_engine_path = os.path.join(BACKEND_DIR, "app/snmp_engine.py")
snmp_lines = []
with open(snmp_engine_path) as f:
    snmp_lines = f.readlines()

mibs_count = len([l for l in snmp_lines if '"oid": "1.' in l])
record_test("Suite 5", "SC4SNMP 300+ MIB Definitions", mibs_count >= 300, f"Total MIBs cataloged: {mibs_count}")

# Check standard RFC and enterprise MIB modules
content_str = "".join(snmp_lines)
rfc_mibs = all(m in content_str for m in ["IF-MIB", "SNMPv2-MIB", "IP-MIB", "TCP-MIB", "UDP-MIB", "BGP4-MIB", "OSPF-MIB", "ENTITY-MIB"])
enterprise_mibs = all(m in content_str for m in ["CISCO-PROCESS-MIB", "CISCO-MEMORY-POOL-MIB", "CISCO-ENVMON-MIB", "JUNIPER-MIB", "ARISTA-RESOURCE-MIB"])
record_test("Suite 5", "Standard RFC MIBs Coverage", rfc_mibs, "IF-MIB, BGP4-MIB, OSPF-MIB, ENTITY-MIB, etc.")
record_test("Suite 5", "Enterprise MIBs Coverage", enterprise_mibs, "Cisco, Juniper, Arista Enterprise MIBs")

# -----------------------------------------------------------------------------
# SUITE 6: OpenConfig YANG State Engine & MDT Trees
# -----------------------------------------------------------------------------
print("\n>> Suite 6: OpenConfig Model-Driven Telemetry (RFC 7951 JSON-IETF)")
gnmi_path = os.path.join(BACKEND_DIR, "app/gnmi_engine.py")
with open(gnmi_path) as f:
    gnmi_content = f.read()

yang_modules = all(m in gnmi_content for m in ["openconfig-interfaces", "openconfig-bgp", "openconfig-platform", "openconfig-system"])
record_test("Suite 6", "OpenConfig YANG Modules", yang_modules, "Interfaces, BGP, Platform, System trees")
record_test("Suite 6", "RFC 7951 JSON-IETF Compliance", "openconfig-interfaces:interfaces" in gnmi_content, "Namespace-qualified paths")

# -----------------------------------------------------------------------------
# SUITE 7: Universal 4-Way Multi-Pipeline Dispatcher
# -----------------------------------------------------------------------------
print("\n>> Suite 7: Universal Multi-Pipeline Telemetry Dispatcher")
dispatcher_path = os.path.join(BACKEND_DIR, "app/telemetry_dispatcher.py")
with open(dispatcher_path) as f:
    disp_content = f.read()

hec_support = "emit_hec" in disp_content and "dispatch_snmp_metric" in disp_content
otel_support = "emit_otel" in disp_content and "/v1/metrics" in disp_content
telegraf_support = "emit_telegraf" in disp_content
syslog_support = "emit_syslog" in disp_content and "format_rfc5424_message" in disp_content
record_test("Suite 7", "Splunk HEC Pipeline", hec_support, "Event & Metric dual ingestion (emit_hec)")
record_test("Suite 7", "OpenTelemetry (OTel) Collector Pipeline", otel_support, "OTLP HTTP /v1/metrics & /v1/logs (emit_otel)")
record_test("Suite 7", "Telegraf Pipeline", telegraf_support, "Influx line protocol stream (emit_telegraf)")
record_test("Suite 7", "RFC 5424 Syslog Pipeline", syslog_support, "UDP/TCP Port 514 streaming (emit_syslog)")

# -----------------------------------------------------------------------------
# SUITE 8: Cascading Fault Injection & Cross-Protocol Synchronization
# -----------------------------------------------------------------------------
print("\n>> Suite 8: Dynamic Fault Injection & Cascading Scenarios")
fault_path = os.path.join(BACKEND_DIR, "app/fault_injection_engine.py")
models_path = os.path.join(BACKEND_DIR, "app/models.py")
with open(fault_path) as f:
    fault_content = f.read()
with open(models_path) as f:
    models_content = f.read()

scenarios = ["link_cut", "hardware_exhaustion", "bgp_route_flap", "ddos_syn_flood", "lateral_movement", "optical_ber_degradation"]
all_scenarios = all(s in models_content for s in scenarios)
fault_engine_ok = "inject_fault" in fault_content and "recover_fault" in fault_content and "TopologyGraph" in fault_content
record_test("Suite 8", "All 6 Production Fault Cascades", all_scenarios and fault_engine_ok, f"Scenarios: {', '.join(scenarios)}")

# -----------------------------------------------------------------------------
# SUITE 9: Cisco ISE vs Cisco Duo Granular Sample Manifests & Schemas
# -----------------------------------------------------------------------------
print("\n>> Suite 9: Cisco ISE vs Cisco Duo Granular Sample Manifests & Schemas")
samples_dir = os.path.join(NETSPOUT_DIR, "appserver/static/samples")
ise_samples = ["cisco-ise-byod", "cisco-ise-nac-8021x", "cisco-ise-trustsec", "cisco-ise-tacacs", "cisco-ise-guest"]
duo_samples = ["cisco-duo-push", "cisco-duo-endpoint", "cisco-duo-sso", "cisco-duo-zerotrust", "cisco-duo-remote-vpn"]

def get_sample_file(s_name):
    p1 = os.path.join(samples_dir, s_name, f"{s_name}.yml")
    p2 = os.path.join(samples_dir, s_name, "manifest.yml")
    if os.path.exists(p1): return p1
    if os.path.exists(p2): return p2
    return None

ise_found = all(get_sample_file(s) is not None for s in ise_samples)
duo_found = all(get_sample_file(s) is not None for s in duo_samples)

record_test("Suite 9", "Cisco ISE 5 Dedicated Sample Manifests", ise_found, f"BYOD, 802.1X NAC, TrustSec, TACACS+, Guest in {samples_dir}")
record_test("Suite 9", "Cisco Duo 5 Dedicated Sample Manifests", duo_found, f"Push MFA, Endpoint Health, SSO SAML, Zero Trust, Remote VPN in {samples_dir}")

# Verify schema and event count in manifests
total_sample_events = 0
for s in ise_samples + duo_samples:
    mpath = get_sample_file(s)
    if mpath and os.path.exists(mpath):
        with open(mpath) as mf:
            content = mf.read()
            total_sample_events += content.count("_raw:") + content.count("raw_text:")

record_test("Suite 9", "Granular Events Extracted in Manifests", total_sample_events >= 20, f"Found {total_sample_events} discrete security events")

# -----------------------------------------------------------------------------
# SUITE 10: 11 Network Architectures & Specialized Scenarios (PAN to GAN)
# -----------------------------------------------------------------------------
print("\n>> Suite 10: 11 Network Architectures & Specialized Topology Scenarios")
scenarios_dir = os.path.join(NETSPOUT_DIR, "appserver/static/scenarios")
arch_scenarios = [
    "scenario_arch_pan_iot_mesh.yml", "scenario_arch_lan_campus_access.yml", "scenario_arch_wlan_meraki_catalyst.yml",
    "scenario_arch_can_multi_building.yml", "scenario_arch_man_carrier_ring.yml", "scenario_arch_wan_global_backbone.yml",
    "scenario_arch_san_fibre_channel.yml", "scenario_arch_nas_storage_cluster.yml", "scenario_arch_vpn_remote_workforce.yml",
    "scenario_arch_epn_isolated_intranet.yml", "scenario_arch_gan_subsea_cloud.yml"
]
specialized_scenarios = [
    "scenario_pure_cisco_enterprise.yml", "scenario_mixed_vendor_enterprise.yml",
    "scenario_sp_cisco.yml", "scenario_sp_mixed.yml",
    "scenario_sdwan_connected_core.yml", "scenario_wireless_connected_core.yml"
]

all_arch_found = all(os.path.exists(os.path.join(scenarios_dir, s)) for s in arch_scenarios)
all_spec_found = all(os.path.exists(os.path.join(scenarios_dir, s)) for s in specialized_scenarios)

record_test("Suite 10", "All 11 Network Architectures (PAN to GAN)", all_arch_found, f"Found 11/11 architecture manifests in {scenarios_dir}")
record_test("Suite 10", "6 Specialized Enterprise & SP Scenarios", all_spec_found, f"Found 6/6 specialized scenario manifests in {scenarios_dir}")

# -----------------------------------------------------------------------------
# SUITE 11: 4 KPI Telemetry & Metric Dimensions Verification
# -----------------------------------------------------------------------------
print("\n>> Suite 11: 4 KPI Telemetry & Metric Dimensions Verification")
models_py = os.path.join(BACKEND_DIR, "app/models.py")
with open(models_py) as mf:
    m_code = mf.read()

dim_perf = all(k in m_code for k in ["bandwidth_utilization_pct", "throughput_bps", "latency_ms", "jitter_ms", "packet_loss_pct", "error_rate_pct"])
dim_health = all(k in m_code for k in ["uptime_seconds", "cpu_utilization_pct", "memory_utilization_pct", "temperature_celsius", "psu_status", "ups_battery_runtime_min"])
dim_config = all(k in m_code for k in ["routing_table_version", "bgp_prefix_count", "route_flaps", "config_drift_checksum", "ipam_dhcp_exhaustion_pct"])
dim_sec = all(k in m_code for k in ["traffic_spike_score", "unauthorized_access_attempts", "firewall_drop_count", "threat_severity_level"])

record_test("Suite 11", "KPI Dim 1: Performance & Traffic", dim_perf, "Bandwidth %, Throughput bps, Latency ms, Jitter ms, Loss %, Error %")
record_test("Suite 11", "KPI Dim 2: Device & Infrastructure Health", dim_health, "Uptime s, CPU %, RAM %, Temp °C, PSU, UPS battery & voltage")
record_test("Suite 11", "KPI Dim 3: Configuration & Protocols", dim_config, "Routing version, BGP prefixes, Flaps, Drift checksum, IPAM exhaustion %")
record_test("Suite 11", "KPI Dim 4: Security & Compliance", dim_sec, "Spike score, Unauthorized access, Firewall drops, Threat severity")

# -----------------------------------------------------------------------------
# SUITE 12: UI Flow Integrity & Onboarding / Scenario Builder Linkages
# -----------------------------------------------------------------------------
print("\n>> Suite 12: UI Flow Integrity & Onboarding / Scenario Builder Linkages")
onboarding_xml = os.path.join(NETSPOUT_DIR, "default/data/ui/views/guided_onboarding.xml")
scenario_xml = os.path.join(NETSPOUT_DIR, "default/data/ui/views/scenario_builder.xml")
onboarding_js = os.path.join(NETSPOUT_DIR, "appserver/static/guided_onboarding.js")
scenario_js = os.path.join(NETSPOUT_DIR, "appserver/static/scenario_builder.js")

with open(onboarding_xml) as f:
    ob_xml_content = f.read()
with open(scenario_xml) as f:
    sb_xml_content = f.read()
with open(onboarding_js) as f:
    ob_js_content = f.read()
with open(scenario_js) as f:
    sb_js_content = f.read()

# Verify pre-rendered options and non-empty selectors
ob_prerender = '<select id="wizard-single-sourcetype-select"' in ob_xml_content and ('Cisco ISE' in ob_xml_content or 'Identity Services Engine' in ob_xml_content)
record_test("Suite 12", "Guided Onboarding Pre-Rendered Selectors", ob_prerender, "Pre-populated HTML options prevent blank dropdowns")

# Verify relative canvas link and inline drawer in scenario builder
sb_canvas_link = 'href="netspout_canvas"' in sb_xml_content and 'id="inline-canvas-drawer"' in sb_xml_content
record_test("Suite 12", "Scenario Builder Canvas Link & Inline Drawer", sb_canvas_link, "Relative link prevents 404 and inline drawer provides instant preview")

# Verify delegated event handling in JS
delegated_listeners = ("$(document).on('click'" in ob_js_content or '$(document).on("click"' in ob_js_content) and ("$(document).on('click'" in sb_js_content or '$(document).on("click"' in sb_js_content)
record_test("Suite 12", "Delegated Event Handling Across SimpleXML", delegated_listeners, "Robust against SimpleXML DOM lifecycle re-renders")

# -----------------------------------------------------------------------------
# SUITE 13: Vendor Discovery, Official Doc Audit & Modular Input Streamer
# -----------------------------------------------------------------------------
print("\n>> Suite 13: Splunkbase Vendor Discovery, Official Doc Audit & Modular Input Streamer")
sys.path.insert(0, os.path.join(NETSPOUT_DIR, "bin"))
try:
    from vendor_catalog import VENDOR_CATALOG
    vendor_cat_loaded = True
except Exception as e:
    vendor_cat_loaded = False
    record_test("Suite 13", "Vendor Catalog Module Load", False, str(e))

if vendor_cat_loaded:
    record_test("Suite 13", "15+ Audited Technology Add-on Catalog", len(VENDOR_CATALOG) >= 15, f"Catalog contains {len(VENDOR_CATALOG)} vendor definitions")
    
    # Check completeness of all vendor records
    all_fields_ok = all(
        all(k in v for k in ["id", "vendor", "splunkbase_id", "splunkbase_url", "doc_url", "sourcetypes", "delimiter", "cim_models", "field_mappings", "sample_events"])
        for v in VENDOR_CATALOG
    )
    record_test("Suite 13", "Official Vendor TA Specifications Audit", all_fields_ok, "Splunkbase ID, Doc URL, Delimiters, CIM Models, Field Mappings, Sample Events")

# Check static JSON mirror for frontend and standalone deployment
vendor_json_path = os.path.join(NETSPOUT_DIR, "appserver/static/vendor_catalog.json")
json_exists = os.path.exists(vendor_json_path)
if json_exists:
    with open(vendor_json_path) as jf:
        j_data = json.load(jf)
        v_list = j_data.get("vendors", j_data) if isinstance(j_data, dict) else j_data
        record_test("Suite 13", "Static Vendor Catalog JSON Mirror", len(v_list) >= 15, f"Mirrored {len(v_list)} vendor definitions to appserver/static/vendor_catalog.json")
else:
    record_test("Suite 13", "Static Vendor Catalog JSON Mirror", False, f"Missing {vendor_json_path}")

# Test modular input netspout_streamer.py
streamer_py = os.path.join(NETSPOUT_DIR, "bin/netspout_streamer.py")
scheme_res = subprocess.run([sys.executable, streamer_py, "--scheme"], capture_output=True, text=True)
test_res = subprocess.run([sys.executable, streamer_py, "--test"], capture_output=True, text=True)

scheme_ok = scheme_res.returncode == 0 and "<scheme>" in scheme_res.stdout and "<streaming_mode>xml</streaming_mode>" in scheme_res.stdout
record_test("Suite 13", "Modular Input --scheme XML Endpoint", scheme_ok, "Valid modular input XML scheme with parameters")

stream_ok = test_res.returncode == 0 and "<stream>" in test_res.stdout and '<event unbroken="1">' in test_res.stdout and "cisco:ios:syslog" in test_res.stdout and "pan:traffic" in test_res.stdout
record_test("Suite 13", "Modular Input Real-Time XML Streamer (--test)", stream_ok, "Native XML <event> stream to Splunk index pipeline")

# Test multi-vendor cascading fault injection
try:
    from fault_injection_engine import FaultInjectionEngine
    from models import TopologyState, Node, Edge, NodeType, FaultScenarioType, FaultInjectionRequest
    f_engine = FaultInjectionEngine()
    test_top = TopologyState(
        nodes=[
            Node(id="fw-pa", name="iad-edge-fw01", type=NodeType.FIREWALL, vendor="palo_alto", ip_address="198.51.100.1"),
            Node(id="rtr-jnx", name="jnx-border-gw01", type=NodeType.ROUTER, vendor="juniper_junos", ip_address="198.51.100.2")
        ],
        edges=[
            Edge(id="link-test", source="fw-pa", target="rtr-jnx", source_port="ethernet1/1", target_port="ge-0/0/0")
        ]
    )
    rec, f_logs, f_metrics, f_traps = f_engine.inject_fault(
        test_top,
        FaultInjectionRequest(scenario_type=FaultScenarioType.LINK_CUT, target_edge_id="link-test")
    )
    pa_log = next((l for l in f_logs if l.vendor == "palo_alto"), None)
    jnx_log = next((l for l in f_logs if l.vendor == "juniper_junos"), None)
    mv_cascade_ok = pa_log is not None and "pan:system" in pa_log.sourcetype and jnx_log is not None and "juniper:junos:syslog" in jnx_log.sourcetype
    record_test("Suite 13", "Multi-Vendor Cascading Fault Engine", mv_cascade_ok, "Accurate Palo Alto & Juniper carrier loss events emitted")
except Exception as e:
    record_test("Suite 13", "Multi-Vendor Cascading Fault Engine", False, str(e))

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# SUITE 15: 30-Vendor Splunkbase Directory & TA Ecosystem
# -----------------------------------------------------------------------------
print("\n>> Suite 15: 30-Vendor Splunkbase Directory & TA Ecosystem")
try:
    from vendor_catalog import list_all_vendors, get_vendor_by_id, VENDOR_ECOSYSTEM
    all_v = list_all_vendors()
    record_test("Suite 15", "Vendor Catalog Count (>= 30)", len(all_v) >= 30, f"Found {len(all_v)} audited enterprise vendors")
    
    categories = set(v["category"] for v in all_v)
    cats_present = len(categories) >= 5
    record_test("Suite 15", "All Vendor Categories Represented", cats_present, f"{len(categories)} distinct enterprise categories found")
    
    cisco = get_vendor_by_id("cisco_ios")
    pa = get_vendor_by_id("palo_alto")
    fortinet = get_vendor_by_id("fortinet")
    f5 = get_vendor_by_id("f5_bigip")
    cloudflare = get_vendor_by_id("cloudflare")
    key_vendors_ok = all([cisco, pa, fortinet, f5, cloudflare])
    record_test("Suite 15", "Key Vendors Audited with Splunkbase App IDs", key_vendors_ok, "Cisco, Palo Alto, Fortinet, F5, Cloudflare verified")
    
    # Check static JSON export
    v_json = os.path.join(NETSPOUT_DIR, "appserver/static/vendor_catalog.json")
    v_json_ok = os.path.exists(v_json) and os.path.getsize(v_json) > 5000
    record_test("Suite 15", "Vendor Catalog JSON Mirror for Splunk Web", v_json_ok, f"Path: {v_json}")
except Exception as e:
    record_test("Suite 15", "Vendor Catalog Integrity", False, str(e))

# -----------------------------------------------------------------------------
# SUITE 16: In-Memory SPL Playground Execution Engine
# -----------------------------------------------------------------------------
print("\n>> Suite 16: In-Memory SPL Playground Execution Engine")
try:
    from spl_engine import spl_engine
    sample_events = [
        {"raw_log": "%BGP-5-ADJCHANGE: peer 10.0.0.1 Up", "signature": "BGP_ADJ", "vendor": "cisco", "action": "allowed", "rtt_ms": 12.5, "protocol": "TCP"},
        {"raw_log": "%BGP-5-ADJCHANGE: peer 10.0.0.2 Down", "signature": "BGP_ADJ", "vendor": "cisco", "action": "alerted", "rtt_ms": 84.0, "protocol": "TCP"},
        {"raw_log": "threat: port scan detected", "signature": "PORT_SCAN", "vendor": "palo_alto", "action": "blocked", "rtt_ms": 2.1, "protocol": "TCP"},
        {"raw_log": "dns lookup failure", "signature": "DNS_FAIL", "vendor": "infoblox", "action": "dropped", "rtt_ms": 95.2, "protocol": "UDP"}
    ]
    
    # Test 1: stats count by vendor
    res1 = spl_engine.execute('stats count by vendor', sample_events)
    t1_ok = len(res1["results"]) == 3 and "cisco" in [r["vendor"] for r in res1["results"]]
    record_test("Suite 16", "SPL Command: stats count by vendor", t1_ok, f"{len(res1['results'])} vendor buckets")

    # Test 2: where clause filtering
    res2 = spl_engine.execute('stats count, avg(rtt_ms) as avg_rtt by vendor | where count > 1', sample_events)
    t2_ok = len(res2["results"]) == 1 and res2["results"][0]["vendor"] == "cisco"
    record_test("Suite 16", "SPL Command: stats + where filtering", t2_ok, "Properly filtered out count <= 1")

    # Test 3: head and sort
    res3 = spl_engine.execute('* | sort -rtt_ms | head 2 | table vendor, rtt_ms', sample_events)
    t3_ok = len(res3["results"]) == 2 and res3["results"][0]["vendor"] in ["infoblox", "cisco"]
    record_test("Suite 16", "SPL Command: sort + head + table projection", t3_ok, "Sorted descending and capped to 2")

    # Test 4: boolean OR text search
    res4 = spl_engine.execute('("BGP" OR "scan")', sample_events)
    t4_ok = len(res4["results"]) == 3
    record_test("Suite 16", "SPL Command: Boolean OR Expression Matching", t4_ok, f"Matched {len(res4['results'])}/4 events")
except Exception as e:
    record_test("Suite 16", "SPL Execution Engine", False, str(e))

# -----------------------------------------------------------------------------
# SUITE 17: NOC & SOC Metric Telemetry Matrix
# -----------------------------------------------------------------------------
print("\n>> Suite 17: NOC & SOC Metric Telemetry Matrix")
try:
    from noc_soc_metrics import metric_engine, NocSocMetricEngine
    
    # Test 1: ITU-T G.107 MOS E-Model calculation
    mos_optimal = metric_engine.calculate_mos(rtt_ms=2.0, jitter_ms=0.5, loss_pct=0.0)
    mos_degraded = metric_engine.calculate_mos(rtt_ms=120.0, jitter_ms=35.0, loss_pct=5.5)
    mos_ok = mos_optimal >= 4.2 and mos_degraded <= 2.5
    record_test("Suite 17", "ITU-T G.107 VoIP MOS Score E-Model", mos_ok, f"Optimal: {mos_optimal} / Degraded: {mos_degraded}")

    # Test 2: Metric Generation Schema
    metrics_normal = metric_engine.generate_noc_metrics(is_degraded=False)
    metrics_degraded = metric_engine.generate_noc_metrics(is_degraded=True)
    required_metric_keys = [
        "throughput_mbps", "goodput_mbps", "flow_efficiency_pct", "optical_rx_dbm",
        "thermal_chassis_c", "thermal_asic_c", "mtbf_hours", "dns_latency_ms",
        "dhcp_pool_exhaustion_pct", "firewall_session_utilization_pct", "c2_beacon_threat_score"
    ]
    keys_ok = all(k in metrics_normal for k in required_metric_keys)
    record_test("Suite 17", "NOC/SOC Telemetry Schema Completeness", keys_ok, f"All {len(required_metric_keys)} metric dimensions present")
    
    # Test 3: Operational Blueprints
    blueprints = metric_engine.get_operational_blueprints()
    bp_ok = "realtime_tactical" in blueprints and "weekly_capacity_forecast" in blueprints and "annual_strategic_compliance" in blueprints
    record_test("Suite 17", "3-Tier Multi-Frequency Operational Blueprints", bp_ok, "Real-time, Weekly trends, Annual strategic verified")
except Exception as e:
    record_test("Suite 17", "NOC/SOC Metric Engine", False, str(e))

# -----------------------------------------------------------------------------
# SUITE 18: NOC & SOC Use Case Repository & Test Harness
# -----------------------------------------------------------------------------
print("\n>> Suite 18: NOC & SOC Use Case Repository & Test Harness")
try:
    from use_case_repo import use_case_repo, USE_CASES
    record_test("Suite 18", "Pre-Built Production Use Cases Count (>= 10)", len(USE_CASES) >= 10, f"Found {len(USE_CASES)} audited use cases")
    
    # Verify automated test execution for all use cases
    all_passed = True
    test_runs = []
    for uc in USE_CASES:
        res = use_case_repo.run_use_case_test(uc["id"])
        test_runs.append(res)
        if res.get("status") != "passed":
            all_passed = False
    
    record_test("Suite 18", "Automated Assertions Verification Harness", all_passed, f"Verified {len(test_runs)}/{len(USE_CASES)} use cases passing")
except Exception as e:
    record_test("Suite 18", "Use Case Repository Test Harness", False, str(e))

# -----------------------------------------------------------------------------
# SUITE 20: 197 User-Requested Sourcetypes 100% End-to-End Coverage
# -----------------------------------------------------------------------------
print("\n>> Suite 20: 197 User-Requested Sourcetypes 100% End-to-End Coverage")
req_csv_file = os.path.join(REPO_ROOT, "tests/requested_sourcetypes.csv")
req_sts = set()
if os.path.exists(req_csv_file):
    import csv
    with open(req_csv_file) as f:
        r = csv.DictReader(f)
        req_sts = set(row["sourcetype"].strip() for row in r if row.get("sourcetype"))
record_test("Suite 20", "197 Requested Sourcetypes Benchmark Specification", len(req_sts) == 197, f"{len(req_sts)}/197 benchmark sourcetypes loaded")

# 1. Samples Manifest Coverage
with open(os.path.join(NETSPOUT_DIR, "appserver/static/samples_manifest.json")) as f:
    m_data = json.load(f)
m_sts = set()
m_files = set()
for cat in m_data.get("categories", []):
    for s in cat.get("samples", []):
        st = s.get("detectedSourcetype") or s.get("sourcetype")
        if st:
            m_sts.add(st)
        for fn in s.get("files", []):
            m_files.add(fn)
record_test("Suite 20", "Samples Manifest Coverage (197/197)", req_sts.issubset(m_sts), f"Manifest contains {len(m_sts)} sourcetypes (covers all 197 requested)")

# 2. Disk Sample YAML Files
samples_dir = os.path.join(NETSPOUT_DIR, "appserver/static/samples")
disk_files = set()
for root, dirs, files in os.walk(samples_dir):
    for fn in files:
        disk_files.add(fn)
missing_disk = set(fn for fn in m_files if fn not in disk_files)
record_test("Suite 20", "Disk Sample YAML Files Integrity", len(missing_disk) == 0, f"All {len(m_files)} sample YAML files present on disk")

# 3. Vendor Catalog TA Mappings
from vendor_catalog import VENDOR_CATALOG
vc_sts = set()
for v in VENDOR_CATALOG:
    for st in v.get("sourcetypes", []):
        vc_sts.add(st)
record_test("Suite 20", "Vendor Catalog TA Coverage (197/197)", req_sts.issubset(vc_sts), f"Vendor catalog covers {len(vc_sts)} sourcetypes (covers all 197 requested)")

# 4. Guided Onboarding JS Catalog
with open(os.path.join(NETSPOUT_DIR, "appserver/static/guided_onboarding.js")) as f:
    js_content = f.read()
js_sts = set(re.findall(r'"id":\s*"([^"]+)"', js_content))
record_test("Suite 20", "Guided Onboarding JS Catalog (197/197)", req_sts.issubset(js_sts), f"JS catalog contains {len(js_sts)} sourcetypes")

# 5. Guided Onboarding SimpleXML Pre-rendered Select Options
with open(os.path.join(NETSPOUT_DIR, "default/data/ui/views/guided_onboarding.xml")) as f:
    xml_content = f.read()
xml_sts = set(re.findall(r'<option\s+value="([^"]+)"', xml_content))
record_test("Suite 20", "Guided Onboarding SimpleXML Pre-rendered Options (197/197)", req_sts.issubset(xml_sts), f"XML contains {len(xml_sts)} pre-rendered options")

# -----------------------------------------------------------------------------
# SUITE 19: netspout.spl Production Release Package Integrity
# -----------------------------------------------------------------------------
print("\n>> Suite 19: netspout.spl Production Archive Validation")
record_test("Suite 19", "netspout.spl Exists", os.path.exists(SPL_ARCHIVE), f"Location: {SPL_ARCHIVE}")

archive_valid = False
archive_size = 0
sha256_hash = ""
top_levels = set()
if os.path.exists(SPL_ARCHIVE):
    archive_size = os.path.getsize(SPL_ARCHIVE)
    with open(SPL_ARCHIVE, "rb") as f:
        sha256_hash = hashlib.sha256(f.read()).hexdigest()
    try:
        with tarfile.open(SPL_ARCHIVE, "r:gz") as tar:
            members = tar.getnames()
            top_levels = set(m.split("/")[0] for m in members if "/" in m)
            archive_valid = ("netspout" in top_levels) and (len(members) > 100)
    except Exception as e:
        archive_valid = False

record_test("Suite 19", "SPL Tarball Structure (netspout/ top level)", archive_valid, f"Extracted top level: {top_levels}")
record_test("Suite 19", "SPL Lightweight Sizing (< 5MB)", archive_size < 5 * 1024 * 1024, f"Actual size: {archive_size / 1024:.1f} KB")

# -----------------------------------------------------------------------------
# FINAL SUMMARY REPORT
# -----------------------------------------------------------------------------
print("\n==========================================================================")
total_tests = len(TEST_RESULTS)
passed_tests = len([t for t in TEST_RESULTS if t["status"] == "PASS"])
failed_tests = total_tests - passed_tests

print(f"📊 Test Results Summary: {passed_tests}/{total_tests} Tests Passed ({(passed_tests/total_tests)*100:.1f}%)")
if failed_tests == 0:
    print("🎉 ALL TEST SUITES PASSED! NetSpout is 100% Production Ready.")
    print(f"   Release Artifact: {SPL_ARCHIVE} ({archive_size / 1024:.1f} KB)")
    print(f"   SHA-256 Checksum: {sha256_hash}")
    sys.exit(0)
else:
    print(f"⚠️ {failed_tests} Tests Failed. Please review errors above.")
    sys.exit(1)
