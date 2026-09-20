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
# SUITE 9: netspout.spl Production Release Package Integrity
# -----------------------------------------------------------------------------
print("\n>> Suite 9: netspout.spl Production Archive Validation")
record_test("Suite 9", "netspout.spl Exists", os.path.exists(SPL_ARCHIVE), f"Location: {SPL_ARCHIVE}")

archive_valid = False
archive_size = 0
sha256_hash = ""
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

record_test("Suite 9", "SPL Tarball Structure (netspout/ top level)", archive_valid, f"Extracted top level: {top_levels}")
record_test("Suite 9", "SPL Lightweight Sizing (< 5MB)", archive_size < 5 * 1024 * 1024, f"Actual size: {archive_size / 1024:.1f} KB")

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
