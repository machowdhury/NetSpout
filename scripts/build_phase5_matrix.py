#!/usr/bin/env python3
"""Phase 5: master compatibility matrix, vendor coverage, mismatch report, ingestion classification and top-10 shortlist.

Inputs (all derived/in-repo; the packages themselves are read only for the format check, in memory, and never copied):
  docs/verification/evidence/ta_inventory/all_packages.json   (scripts/phase5_inventory.py)
  docs/reference/sourcetype_coverage.json + catalog/vendors.json   (NetSpout catalog: 349 sourcetypes, 88 vendors)
  docs/verification/evidence/sample_replay/sample_inventory.json   (shipped YAML samples + external corpus, already inventoried)
  docs/contracts/ta_live_results.json                          (the only source of live Splunk verification)
Outputs: docs/contracts/phase5/*

Match types (evidence-based):
  exact      the catalog sourcetype name is literally defined by a downloaded package (file:stanza recorded)
  conflict   a package covers the vendor and defines a DIFFERENT name that is a close counterpart (name similarity >= 0.8), or the exact name has a payload/routing conflict
  candidate  a downloaded package names the vendor/product, but no sourcetype of it corresponds; coverage is unconfirmed
  none       no downloaded package covers the vendor
Nothing here sets SPLUNK_VERIFIED; that comes only from ta_live_results.json.
"""
import csv
import difflib
import fnmatch
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from build_ta_registry import format_check, load_ta_defs, payload_format  # noqa: E402

PACKS = Path("~/netspout/private-packs").expanduser()
EVID = ROOT / "docs/verification/evidence"
OUT = ROOT / "docs/contracts/phase5"

# catalog vendor id -> add-on ids whose app.conf label/id names that vendor's product. This is identification of coverage candidates by name, nothing more:
# a package only becomes an exact match through a sourcetype defined in its configuration.
VENDOR_PACKAGES = {
    "arista_eos": ["aristanetworks"], "aruba_cx": ["TA-aruba_networks"], "cisco_asa": ["Splunk_TA_cisco-asa", "CiscoSecurityCloud"], "cisco_catalyst": ["TA_cisco_catalyst"],
    "cisco_duo": ["CiscoSecurityCloud"], "cisco_intersight": ["Splunk_TA_Cisco_Intersight"], "cisco_ios": ["TA_cisco_catalyst"], "cisco_ise": ["Splunk_TA_cisco-ise", "TA_cisco_catalyst"],
    "cisco_meraki": ["Splunk_TA_cisco_meraki"], "cisco_sdwan": ["TA_cisco_catalyst"], "citrix_netscaler": ["Splunk_TA_citrix-netscaler"], "cloudflare": ["cloudflare", "TA_cloudflare_r2"],
    "extrahop": ["TA-extrahop_addon"], "f5_bigip": ["Splunk_TA_f5-bigip"], "fortinet": ["Splunk_TA_fortinet_fortigate"], "juniper_junos": ["Splunk_TA_juniper"], "netscout": ["Omnis_Streamer-TA"],
    "netskope": ["TA-NetSkopeAppForSplunk"], "palo_alto": ["Splunk_TA_paloalto_networks"], "sonicwall": ["sonicwall_sma1000_ta"],
    "sophos": ["TA-sophos_xg_firewall", "TA-sophos-central-cef", "TA-sophos-email-security"],
    "splunk": ["Splunk_TA_stream_wire_data", "Splunk_TA_stream", "splunk_app_stream_ipfix_cisco_hsl"],
    "vmware_nsx": ["TA-nsx", "Splunk_TA_vmware", "TA-vmware-vision", "TA-vmware_esxi_syslog", "Splunk_TA_vmware_inframon"], "zscaler_zia": ["TA-Zscaler_CIM"],
    "microsoft_windows": ["Splunk_TA_windows", "Splunk_TA_microsoft_sysmon", "SA-admon"], "crowdstrike": ["Splunk_TA_CrowdStrike_FDR", "TA-crowdstrike-falcon-event-streams", "TA_crowdstrike_falcon_detections", "TA-crowdstrike_falcon_discover"],
    "amazon_aws": ["Splunk_TA_aws", "SA-aws_security_hub"], "microsoft_365": ["splunk_ta_o365", "TA_MS_Teams", "Splunk_TA_MS_Security"], "microsoft_azure": ["TA-MS-AAD", "Splunk_TA_microsoft-cloudservices"],
    "okta": ["Splunk_TA_okta_identity_cloud"], "suricata_oisf": ["Splunk_TA_CCX_Suricata"], "linux_infrastructure": ["Splunk_TA_nix"], "osquery": ["TA-OSqueryv1"], "google_workspace": ["Splunk_TA_Google_Workspace"],
    "google_cloud": ["Splunk_TA_google-cloudplatform"], "opentelemetry": ["Splunk_TA_otel_windows_x86_64"], "docker": ["TA-docker-add-on-for-splunk"],
    "broadcom_symantec": ["Splunk_TA_bluecoat-proxysg", "Splunk_TA_symantec-ep", "Splunk_TA_CCX_Symantec_BlueCoat_ProxySG_Extensions"], "atlassian": ["confluence_and_jira_audit_addon_for_splunk", "bitbucket_addon_for_splunk"],
    "nginx_f5": ["Splunk_TA_nginx"], "proofpoint": ["TA-bxti-proofpoint-ser", "TA-pps_ondemand", "TA-proofpoint-casb-addon-for-splunk", "TA-proofpoint-incidents"], "sysdig": ["TA-Sysdig"],
    "sailpoint": ["TA-sailpoint-identitynow-auditevent-add-on"], "imperva": ["Splunk_TA_CCX_Imperva_WAF"], "barracuda": ["BarracudaEGD"], "tenable": ["TA-tenable"], "slack": ["TA-slack-add-on-for-splunk"],
    "gitlab": ["TA-gitlab-add-on-for-splunk", "TA-gitlab-saas-add-on-for-splunk", "TA_gitlab"], "qualys": ["TA-Qualys-Cloud-Connector"], "rapid7": ["TA-rapid7-insightvm", "TA-insightappsec"], "tanium": ["TA-Tanium"],
    "trellix_mcafee": ["Trellix_Splunk"], "elastic": ["TA-elastic-search"]}

# monitored-product vendor of each app, from its app.conf label/id (used only to count distinct vendors represented by the packages)
VENDOR_RULES = [(r"cisco|CiscoSecurity|meraki|thousandeyes|intersight|Omnis", "Cisco"), (r"omnis|netscout", "NETSCOUT"), (r"aws|amazon|athena", "Amazon"), (r"azure|microsoft|windows|sysmon|admon|MS_|MS-AAD|defender", "Microsoft"),
                (r"google|chrome", "Google"), (r"crowdstrike", "CrowdStrike"), (r"proofpoint|pps_ondemand|bxti", "Proofpoint"), (r"palo|paloalto", "Palo Alto Networks"), (r"fortinet|fortigate|fortindr", "Fortinet"),
                (r"vmware|Hydra|nsx|esxi", "VMware"), (r"sophos", "Sophos"), (r"gitlab", "GitLab"), (r"atlassian|bitbucket|confluence|jira", "Atlassian"), (r"rapid7|insightvm|insightappsec", "Rapid7"), (r"CCX_Unified_Trend|trend", "Trend Micro"),
                (r"bluecoat|symantec|Blue Coat", "Broadcom/Symantec"), (r"f5|nginx", "F5"), (r"juniper", "Juniper"), (r"citrix", "Citrix"), (r"aruba", "HPE Aruba"), (r"blue ?cat", "BlueCat"), (r"akamai|guardicore|ensign", "Akamai"),
                (r"cloudflare", "Cloudflare"), (r"splunk|SA-|stream|db_connect|JDBC|otel|snow|salesforce|nix|apache|mysql|dynatrace", None)]
APP_VENDOR_OVERRIDES = {"Splunk_TA_Dynatrace": "Dynatrace", "Splunk_TA_snow": "ServiceNow", "Splunk_TA_salesforce": "Salesforce", "Splunk_TA_nix": "Unix/Linux (open source)", "Splunk_TA_apache": "Apache (open source)",
                        "Splunk_TA_mysql": "MySQL/Oracle", "Splunk_TA_nginx": "F5", "Splunk_TA_stream": "Splunk", "Splunk_TA_stream_wire_data": "Splunk", "splunk_app_db_connect": "Splunk", "Splunk_TA_otel_windows_x86_64": "Splunk/OpenTelemetry",
                        "Splunk_TA_bit9-carbonblack": "VMware/Carbon Black", "SA-Hydra": "VMware", "SA-Hydra-inframon": "VMware", "Splunk_TA_infoblox": "Infoblox", "Splunk_TA_cyberark": "CyberArk", "Splunk_TA_cyberark_epm": "CyberArk",
                        "Splunk_TA_okta_identity_cloud": "Okta", "Splunk_TA_symantec-ep": "Broadcom/Symantec", "Splunk_TA_bluecoat-proxysg": "Broadcom/Symantec", "Splunk_TA_CCX_Symantec_BlueCoat_ProxySG_Extensions": "Broadcom/Symantec",
                        "TA-ONTAP-FieldExtractions": "NetApp", "TA-cisco-cloud-security-addon": "Cisco", "TA_Stormshield": "Stormshield", "TA-Zscaler_CIM": "Zscaler", "TA-NetSkopeAppForSplunk": "Netskope", "TA-Tanium": "Tanium",
                        "TA-Illumio": "Illumio", "TA-JamfProtect": "Jamf", "TA-Qualys-Cloud-Connector": "Qualys", "TA-tenable": "Tenable", "TA-Sysdig": "Sysdig", "TA-OSqueryv1": "osquery (open source)", "TA-macOS": "Apple",
                        "ServiceNow_TA_windows_linux_assets": "ServiceNow", "ansible_addon_for_splunk": "Red Hat", "TA-docker-add-on-for-splunk": "Docker", "TA-extrahop_addon": "ExtraHop", "TA-wiz-addon-for-splunk": "Wiz",
                        "TA-slack-add-on-for-splunk": "Slack", "TA-siemplify": "Google (Siemplify)", "TA-Varonis-DatAlert": "Varonis", "Splunk_TA_CCX_Imperva_WAF": "Imperva", "Splunk_TA_CCX_Suricata": "OISF/Suricata",
                        "Splunk_TA_CCX_Abnormal_Security": "Abnormal Security", "Splunk_TA_CCX_Auth0": "Okta/Auth0", "Splunk_TA_CCX_Lacework_Products": "Lacework", "Splunk_TA_CCX_NetSuite_Products": "Oracle NetSuite",
                        "Splunk_TA_CCX_Snowflake_CIM_Support": "Snowflake", "Splunk_TA_CCX_Unified_Trend_Micro": "Trend Micro", "Trellix_Splunk": "Trellix", "BarracudaEGD": "Barracuda", "TA-bigid-audits": "BigID",
                        "TA-acunetix-360-add-on-for-splunk-cloud": "Acunetix", "TA-paloalto-dlp": "Palo Alto Networks", "TA-guardium": "IBM", "TA-ibm_datapower": "IBM", "genesys_cloud_ta": "Genesys",
                        "aristanetworks": "Arista Networks", "TA-auvik-networks-add-on-for-splunk": "Auvik", "TA-aviatrix": "Aviatrix", "TA-cofense-triage-add-on-for-splunk": "Cofense", "TA-cohesity-add-on-for-splunk": "Cohesity",
                        "TA-CYBERHAVEN": "Cyberhaven", "TA-Databricks": "Databricks", "TA_dragos_ot_add_on": "Dragos", "TA-elastic-search": "Elastic", "TA-entrust-datacard-intellitrust-add-on-for-splunk": "Entrust",
                        "TA-flashpoint-intelligence": "Flashpoint", "TA-forescout": "Forescout", "TA-invicti-platform": "Invicti", "TA-ivanti-ism": "Ivanti", "TA-lansweeper-add-on-for-splunk": "Lansweeper",
                        "TA-manageengine-endpoint-central-add-on": "ManageEngine (Zoho)", "TA-manageengine-vulnerability-manager-plus-add-on": "ManageEngine (Zoho)", "TA-site24x7": "ManageEngine (Zoho)",
                        "TA-mandiant-digital-threat-monitoring": "Google (Mandiant)", "TA_menlosecurity_api_inputs": "Menlo Security", "TA-postfix-mail": "Postfix (open source)", "TA-rubric-protocol": "Rubric Protocol",
                        "TA-swift_agi": "SWIFT", "TA-sailpoint-identitynow-auditevent-add-on": "SailPoint", "TA-saviyntevents": "Saviynt", "TA-securelink": "SecureLink", "sonicwall_sma1000_ta": "SonicWall",
                        "Splunk_JDBC_athena": "Splunk", "Splunk_JDBC_mssql": "Splunk", "Splunk_JDBC_mysql": "Splunk", "Splunk_JDBC_oracle": "Splunk", "DA-ESS-OTSecurity": "Splunk", "TA_vectra_detect_json": "Vectra AI",
                        "TA_teamviewer": "TeamViewer", "TA_unifi_ng": "Ubiquiti", "TA-zabbix-add-on-for-splunk": "Zabbix", "TA-zero-networks-add-on-for-splunk": "Zero Networks", "TA-nsx": "VMware", "TA-vmware-vision": "VMware",
                        "TA-vmware_esxi_syslog": "VMware", "TA-Cisco-NVM": "Cisco", "ta_cisco_meeting_server_add_on_for_splunk": "Cisco", "ta_cisco_spaces": "Cisco", "TA-ensign_waf_akamaisiem": "Akamai"}

LIVE = json.loads((ROOT / "docs/contracts/ta_live_results.json").read_text())


def vendor_of_app(app_id, label):
    if app_id in APP_VENDOR_OVERRIDES:
        return APP_VENDOR_OVERRIDES[app_id]
    for rx, v in VENDOR_RULES:
        if re.search(rx, app_id + " " + (label or ""), re.I) and v:
            return v
    return (label or app_id).replace("Add-on", "").replace("for Splunk", "").strip() or app_id


def role_of(rec, kinds, rename):
    if "inputs.conf sourcetype" in kinds:
        return "input (declared in inputs.conf)"
    if "transforms.conf sourcetype override" in kinds:
        return "output (set by a transforms.conf routing rule)"
    if "props.conf rename target" in kinds:
        return "output (rename target)"
    if rename:
        return "legacy name (the add-on renames it)"
    return "props-defined (parse/search-time rules; the package does not declare which input produces it)"


def load_inventory():
    inv = json.loads((EVID / "ta_inventory/all_packages.json").read_text())
    ident = {}                                   # (id, version) -> merged identity; every file path is preserved
    for pkg in inv["packages"]:
        for a in pkg["apps"]:
            k = (a["id"], a["version"])
            e = ident.setdefault(k, dict(a, files=[], vendor_group=vendor_of_app(a["id"], a["label"])))
            e["files"].append(pkg["path"])
    return inv, ident


def ingestion_class(app):
    cfg = sorted({i["mechanism"] + (" (%s)" % i["scheme"] if i.get("scheme") else "") for i in app["ingestion"] if i["basis"] == "config"})
    # a README that merely mentions OpenTelemetry/streaming telemetry/CEF (framework boilerplate, dependency notes) is not evidence of that intake unless the app is itself a telemetry collector
    weak = set() if re.search(r"otel|telemetry|arista", app["id"] + " " + str(app["label"]), re.I) else {"opentelemetry", "streaming_telemetry", "cef"}
    doc = sorted({i["mechanism"] for i in app["ingestion"] if i["basis"] == "readme" and i["mechanism"] not in weak})
    props = [s["props"] for s in app["sourcetypes"] if s["props"]]
    json_events = sum(1 for p in props if (p.get("KV_MODE") or "").lower() == "json" or "json" in (p.get("INDEXED_EXTRACTIONS") or "").lower())
    metric = bool(app["metrics_signals"]["metric_indexes"] or app["metrics_signals"]["props_metric_schema"] or app["metrics_signals"]["transforms_metric_schema"])
    mech = []
    s = " ".join(cfg + doc).lower()
    if any(x in s for x in ("syslog", "network listener", "file monitoring", "monitor")):
        mech.append("syslog/file")
    if "modular input" in s or "rest_api" in s:
        mech.append("REST/API modular input")
    if "hec input" in s or "hec" in doc:
        mech.append("HEC")
    if "netflow_ipfix" in s:
        mech.append("NetFlow/IPFIX")
    if "sflow" in s:
        mech.append("sFlow")
    if "opentelemetry" in s or "streaming_telemetry" in s:
        mech.append("OpenTelemetry/streaming telemetry")
    if "database" in s:
        mech.append("database (JDBC/DB Connect)")
    if "cloud_pull" in s:
        mech.append("cloud service pull")
    if "scripted input" in s:
        mech.append("scripted input")
    if "snmp" in s:
        mech.append("SNMP")
    if metric:
        mech.append("metrics")
    return {"config_declared": cfg, "readme_mentions_only": [d for d in doc if d not in " ".join(cfg).lower()], "payload_shape": "JSON events" if json_events and json_events >= max(1, len(props) // 2) else ("text events" if props else "not declared"),
            "json_sourcetypes": json_events, "metric_definitions": metric, "categories": sorted(set(mech)) or ["not declared by the package (operator chooses syslog, file or HEC)"]}


_PLAIN = {"monitor", "udp", "tcp", "splunktcp", "http", "batch", "fschange"}
_HOST = {"WinEventLog", "perfmon", "WinRegMon", "MonitorNoHandle", "script", "admon", "WinNetMon", "WinPrintMon", "WinHostMon"}


def support_for(app, ac, st=None, props=None):
    """NetSpout delivers HEC JSON events/metrics and syslog, and has NetFlow/IPFIX, SNMP and gNMI exporters. It does not emulate vendor REST APIs, host agents, scripted inputs, JDBC or Stream collectors.
    SUPPORTED_DELIVERY = the add-on's own input for this data is syslog/file/HEC/network text; SUBSTITUTE_VIA_HEC = the real input is an API/agent/script, NetSpout could only deliver equivalent events over HEC; NOT_EMULATED = flow/OTel/database."""
    cats = set(ac["categories"])
    if "database (JDBC/DB Connect)" in cats and len(cats) == 1:
        return "NOT_EMULATED", "database input"
    if cats & {"NetFlow/IPFIX", "sFlow"} and ac["payload_shape"] == "not declared":
        return "NOT_EMULATED", "flow-collector template; defines no sourcetypes"
    if "OpenTelemetry/streaming telemetry" in cats and not (cats & {"syslog/file", "HEC"}):
        return "NOT_EMULATED", "OpenTelemetry/streaming-telemetry intake"
    if st and st.startswith("stream:"):
        return "NOT_EMULATED", "stream:* events are produced by Splunk Stream (streamfwd) from wire/flow data; NetSpout does not emulate the Stream collector"
    if st:
        types = {i["stanza"].split("://")[0] for i in app["inputs"] if i["sourcetype"] == st}
        if types and types <= _PLAIN:
            return "SUPPORTED_DELIVERY", "inputs.conf declares %s input for this sourcetype" % "/".join(sorted(types))
        if types & _HOST:
            return "SUBSTITUTE_VIA_HEC", "inputs.conf declares a host-agent/scripted input (%s); NetSpout does not emulate it" % "/".join(sorted(types & _HOST))
        if types:
            return "SUBSTITUTE_VIA_HEC", "inputs.conf declares a modular input (%s) that pulls from an API or service; NetSpout does not emulate it" % "/".join(sorted(types))
        text = props is not None and (props.get("KV_MODE") or "").lower() != "json" and "json" not in (props.get("INDEXED_EXTRACTIONS") or "").lower()
        if text:
            return "SUPPORTED_DELIVERY", "text sourcetype not tied to an API/agent input in inputs.conf%s (inferred; not a documented statement)" % ("; the package documents syslog/file/HEC intake" if cats & {"syslog/file", "HEC"} else "")
    if not (cats & {"REST/API modular input", "cloud service pull", "scripted input"}):
        return "SUPPORTED_DELIVERY", "no API/agent input declared; the operator chooses syslog, file or HEC"
    return "SUBSTITUTE_VIA_HEC", "the add-on pulls from a vendor API or service; NetSpout does not emulate it, it can only deliver equivalent events over HEC if their payload matches the API output"


def main():
    inv, ident = load_inventory()
    cov = json.loads((ROOT / "docs/reference/sourcetype_coverage.json").read_text())["rows"]
    vendors = {v["id"]: v for v in json.loads((ROOT / "catalog/vendors.json").read_text())}
    samp = json.loads((EVID / "sample_replay/sample_inventory.json").read_text())["rows"]
    by_app = {}
    for (aid, ver), e in ident.items():
        by_app.setdefault(aid, []).append(e)
    # TA sourcetype index: name -> list of {app, version, role, pattern}
    ta_index = defaultdict(list)
    for (aid, ver), e in ident.items():
        for s in e["sourcetypes"]:
            kinds = {d["kind"] for d in s["declared_by"]}
            ta_index[s["sourcetype"]].append({"app": aid, "version": ver, "label": e["label"], "role": role_of(s, kinds, (s["props"] or {}).get("rename")), "pattern": bool(re.search(r"[*?]|\(\?|\\", s["sourcetype"])),
                                              "where": [d["where"] for d in s["declared_by"]], "files": e["files"], "props": s["props"], "eventtypes": s["eventtypes"]})
    patterns = [(n, v) for n, v in ta_index.items() if v[0]["pattern"] and "*" in n]
    # shipped/corpus samples per catalog sourcetype
    samples = defaultdict(lambda: {"shipped_yaml": [], "external_corpus": []})
    for r in samp:
        for st in set(r["catalog_sourcetypes"]):
            (samples[st]["shipped_yaml"] if r["corpus"] == "shipped" else samples[st]["external_corpus"]).append({"file": r["file"], "status": r["status"]})
    from netspout_core.generator_modes import TelemetryGeneratorService, _NATIVE
    svc = TelemetryGeneratorService()
    gen = {}
    for c in cov:
        try:
            ents, prov = svc.prepare_sourcetype_entries(c["vendor_id"], c["sourcetype"], 4)
            raws = [e.raw_log for e in ents]
            gen[c["sourcetype"]] = {"ok": bool(raws), "raws": raws, "mode": "native" if c["sourcetype"] in _NATIVE else (prov or {}).get("mode"), "error": None if raws else "no events produced"}
        except Exception as exc:
            gen[c["sourcetype"]] = {"ok": False, "raws": [], "mode": None, "error": str(exc)[:140]}
    # format check needs the add-on regexes (memory only): load the packages that define an exact catalog name
    catnames = {c["sourcetype"] for c in cov}
    need = sorted({PACKS / f for n in catnames for rec in ta_index.get(n, []) for f in rec["files"][:1]})
    defs = load_ta_defs(need)
    app_cls = {k: ingestion_class(e) for k, e in ident.items()}
    ta_names_by_vendor = {}
    for vid, aids in VENDOR_PACKAGES.items():
        ta_names_by_vendor[vid] = {n: [r for r in recs if r["app"] in aids] for n, recs in ta_index.items() if any(r["app"] in aids and not r["pattern"] for r in recs)}

    rows = []
    for c in cov:
        st, vid = c["sourcetype"], c["vendor_id"]
        g = gen[st]
        exact = [r for r in ta_index.get(st, []) if not r["pattern"]]
        cover = [a for a in VENDOR_PACKAGES.get(vid, []) if a in by_app]
        row = {"catalog_vendor": vid, "catalog_vendor_name": c["vendor"], "catalog_product": c["product"], "catalog_sourcetype": st, "catalog_data_kind": c["data_kind"], "catalog_protocol": c["protocol"],
               "covering_packages": cover, "ta_app_id": None, "package_version": None, "package_files": [], "canonical_ta_sourcetype": None, "ta_sourcetype_role": None, "match_type": "none", "naming_conflict": False,
               "conflicts": [], "generator_tier": c["generator_tier"], "generator_valid": g["ok"], "generator_mode": g["mode"], "generator_error": g["error"], "payload_format": payload_format(g["raws"][0]) if g["raws"] else None,
               "sample_status": None, "shipped_yaml_samples": len(samples[st]["shipped_yaml"]), "external_corpus_samples": len(samples[st]["external_corpus"]), "ta_ingestion": None, "ingestion_support": None,
               "destination": "metric index" if c["data_kind"] == "metric" else "event index", "ta_destination": None, "format_verification": "NOT_APPLICABLE (no exact add-on definition)", "format_detail": None,
               "live_verification": "NOT_VERIFIED", "evidence": [], "scenarios": len(c["scenarios"]), "remediation": []}
        row["sample_status"] = ("SHIPPED_YAML" if samples[st]["shipped_yaml"] else "") + ("+" if samples[st]["shipped_yaml"] and samples[st]["external_corpus"] else "") + ("EXTERNAL_CORPUS" if samples[st]["external_corpus"] else "") or "NONE"
        usable_sample = any(x["status"] == "REPLAYABLE" for x in samples[st]["shipped_yaml"] + samples[st]["external_corpus"])
        row["sample_replayable"] = usable_sample
        if exact:
            lvr = LIVE.get(st) or {}
            rec = next((r for r in exact if lvr.get("passed") and lvr.get("package") in r["files"]), None) or next((r for r in exact if r["app"] in cover), exact[0])
            row.update(match_type="exact", ta_app_id=rec["app"], package_version=rec["version"], package_files=rec["files"], canonical_ta_sourcetype=st, ta_sourcetype_role=rec["role"],
                       evidence=[w + " in " + rec["files"][0] for w in rec["where"]], also_defined_by=sorted({r["app"] for r in exact if r["app"] != rec["app"]}))
            if rec["role"].startswith("legacy"):
                row.update(match_type="conflict", naming_conflict=True, canonical_ta_sourcetype=(rec["props"] or {}).get("rename"))
                row["conflicts"].append("naming: the add-on does not use %r as a sourcetype; it renames it to %r" % (st, (rec["props"] or {}).get("rename")))
            ac = app_cls[(rec["app"], rec["version"])]
            row["ta_ingestion"] = ac["categories"]
            p = rec["props"] or {}
            row["ingestion_support"], row["ingestion_note"] = support_for(ident[(rec["app"], rec["version"])], ac, st, rec["props"])
            metric_ta = bool(p.get("metric_schema")) or bool(ident[(rec["app"], rec["version"])]["metrics_signals"]["metric_indexes"])
            row["ta_destination"] = "metric index (add-on defines a metric schema or metric index)" if metric_ta else "event index (no metric schema in the add-on)"
            if c["data_kind"] == "metric" and not metric_ta:
                row["conflicts"].append("routing: catalog sends metric-index payloads; the add-on defines this as an event sourcetype")
            if c["data_kind"] != "metric" and p.get("metric_schema"):
                row["conflicts"].append("routing: add-on expects metric-index data; catalog sends events")
            if g["raws"]:
                dl = [d for d in defs.get(st, []) if d["app"] == rec["app"]] or defs.get(st, [])
                if dl:
                    fc = format_check(g["raws"], dl[0])
                    row["format_detail"] = {k: v for k, v in fc.items() if k in ("method", "events", "events_with_any_extraction", "partial_column_events", "force_sourcetype_match", "regex_compile_errors", "passes")}
                    if fc["method"] and fc["method"].startswith("json parse"):
                        row["format_verification"] = "STRUCTURE_ONLY" if fc.get("passes") else "FORMAT_CONFLICT"
                    elif fc.get("passes"):
                        row["format_verification"] = "FORMAT_VERIFIED"
                    elif fc.get("events_with_any_extraction") == 0 and fc.get("partial_column_events"):
                        row["format_verification"] = "FORMAT_PARTIAL"
                    elif fc.get("events_with_any_extraction") == 0 and (dl[0]["regexes"] or dl[0]["delims"]):
                        row["format_verification"] = "FORMAT_CONFLICT"
                        row["conflicts"].append("payload-format: none of the add-on's extractions match NetSpout's rendered events")
                    elif fc.get("force_sourcetype_match") == 0:
                        row["format_verification"] = "FORMAT_CONFLICT"
                        row["conflicts"].append("payload-format: events do not match the add-on's sourcetype-routing regex")
                    else:
                        row["format_verification"] = "FORMAT_PARTIAL"
                    if row["format_verification"] == "FORMAT_CONFLICT" and not any(x.startswith("payload-format") for x in row["conflicts"]):
                        row["conflicts"].append("payload-format: rendered events are not the JSON object the add-on expects")
                else:
                    row["format_verification"] = "NOT_CHECKABLE (the add-on defines no extraction rules for this sourcetype)"
            else:
                row["format_verification"] = "NOT_CHECKABLE (NetSpout cannot generate events for this sourcetype)"
            lv = LIVE.get(st)
            if lv and lv.get("passed") and lv["package"] in rec["files"]:
                row["live_verification"] = "SPLUNK_VERIFIED (Phase 4 live evidence, %s %s)" % (lv["package"], lv["version"])
                row["evidence"].append(lv["evidence"])
        elif cover:
            # candidate / conflict: look for a close counterpart name among the covering packages
            best = (0.0, None)
            norm = lambda x: x.replace("_", ":").lower()
            for n, recs in ta_names_by_vendor.get(vid, {}).items():
                if any(r["role"].startswith("legacy") for r in recs):
                    continue
                ratio = difflib.SequenceMatcher(None, norm(st), norm(n)).ratio()
                if ratio > best[0]:
                    best = (ratio, n)
            pm = [n for n, v in patterns if fnmatch.fnmatchcase(st, n) and any(r["app"] in cover for r in v)]
            if best[0] >= 0.8:
                recs = ta_names_by_vendor[vid][best[1]]
                row.update(match_type="conflict", naming_conflict=True, ta_app_id=recs[0]["app"], package_version=recs[0]["version"], package_files=recs[0]["files"], canonical_ta_sourcetype=best[1], ta_sourcetype_role=recs[0]["role"],
                           evidence=["%s in %s" % (recs[0]["where"][0], recs[0]["files"][0])])
                row["conflicts"].append("naming: NetSpout uses %r; the covering add-on defines %r (similarity %.2f; equivalence not confirmed)" % (st, best[1], best[0]))
            elif pm:
                row.update(match_type="candidate", ta_app_id=cover[0], evidence=["props.conf wildcard stanza [%s]" % pm[0]], canonical_ta_sourcetype=pm[0])
                row["conflicts"].append("naming: only a wildcard stanza %r covers this name; no literal definition" % pm[0])
            else:
                row.update(match_type="candidate", ta_app_id=cover[0], package_version=by_app[cover[0]][0]["version"], package_files=by_app[cover[0]][0]["files"])
            ac = app_cls[(row["ta_app_id"], by_app[row["ta_app_id"]][0]["version"])]
            row["ta_ingestion"] = ac["categories"]
            row["ingestion_support"], row["ingestion_note"] = support_for(by_app[row["ta_app_id"]][0], ac)
        else:
            row["ingestion_support"] = "NO_PACKAGE"
        # remediation
        rem = []
        if row["match_type"] == "none":
            rem.append("no downloaded add-on covers this vendor: obtain the vendor's add-on or document the sourcetype as unsupported/self-defined")
        elif row["match_type"] == "candidate":
            rem.append("identify the add-on sourcetype that corresponds to this product (none of the covering package's names matches); do not rename until then")
        if row["naming_conflict"]:
            rem.append("confirm the counterpart name from add-on documentation/samples, then migrate with a registry alias (no mass rename)")
        if any(x.startswith("routing") for x in row["conflicts"]):
            rem.append("align metric/event routing with the add-on (metric index vs event) before any live test")
        if row["format_verification"] in ("FORMAT_CONFLICT", "FORMAT_PARTIAL"):
            rem.append("fix or extend the generator payload so the add-on's own extractions match")
        if row["match_type"] == "exact" and not g["ok"]:
            rem.append("no generator output: add a generator/sample for the exact name (out of scope for Phase 5)")
        if row["match_type"] == "exact" and row["ingestion_support"] in ("SUBSTITUTE_VIA_HEC", "NOT_EMULATED"):
            rem.append("decide: emulate the add-on's input (%s) or mark HEC substitution as the supported path" % row.get("ingestion_note", ""))
        if row["match_type"] == "exact" and g["ok"] and row["live_verification"] == "NOT_VERIFIED" and not row["conflicts"]:
            rem.append("write a spec and run the one-add-on-at-a-time live check (Phase 4 method); only then drop the shadowing HEC fields")
        row["remediation"] = rem
        rows.append(row)

    # ------------------------------------------------------------------ vendor coverage
    vend = []
    for vid, v in sorted(vendors.items(), key=lambda kv: kv[1]["name"].lower()):
        rs = [r for r in rows if r["catalog_vendor"] == vid]
        ex = [r for r in rs if r["match_type"] == "exact"]
        pk = [a for a in VENDOR_PACKAGES.get(vid, []) if a in by_app]
        blockers = []
        if not pk:
            blockers.append("no downloaded add-on covers this vendor")
        if pk and not ex:
            blockers.append("covering add-on defines none of the catalog's sourcetype names")
        if any(r["naming_conflict"] for r in rs):
            blockers.append("%d naming conflicts" % sum(r["naming_conflict"] for r in rs))
        pf = sum(1 for r in ex if any(x.startswith(("payload", "routing")) for x in r["conflicts"]))
        if pf:
            blockers.append("%d exact matches with payload/routing conflicts" % pf)
        if ex and not any(r["live_verification"].startswith("SPLUNK") for r in ex):
            blockers.append("no exact match live-verified")
        if sum(1 for r in rs if not r["generator_valid"]):
            blockers.append("%d sourcetypes have no working generator" % sum(1 for r in rs if not r["generator_valid"]))
        vend.append({"vendor_id": vid, "vendor": v["name"], "products": len({r["catalog_product"] for r in rs}), "catalog_sourcetypes": len(rs), "downloaded_matching_addons": len(pk), "matching_addon_ids": pk,
                     "exact_canonical_matches": len(ex), "naming_conflicts": sum(r["naming_conflict"] for r in rs), "payload_or_routing_conflicts": pf, "valid_generators": sum(r["generator_valid"] for r in rs),
                     "sample_backed": sum(1 for r in rs if r["sample_status"] != "NONE"), "live_verified": sum(1 for r in rs if r["live_verification"].startswith("SPLUNK_VERIFIED")),
                     "specialized_ingestion_required": sum(1 for r in rs if r["ingestion_support"] in ("SUBSTITUTE_VIA_HEC", "NOT_EMULATED") and r["match_type"] != "none"), "main_blockers": blockers})

    # ------------------------------------------------------------------ reconciliation totals
    distinct_st = set(ta_index)
    literal = {n for n, v in ta_index.items() if not v[0]["pattern"]}
    absent = sorted(n for n in literal if n not in catnames)
    vendors_rep = defaultdict(set)
    for k, e in ident.items():
        vendors_rep[e["vendor_group"]].add(k[0])
    publishers = Counter((e.get("publisher") or "(none declared)").strip() for e in ident.values())
    totals = {"package_files": len(inv["packages"]), "files_inspected": inv["summary"]["inspected"], "files_failed": inv["summary"]["failed"], "byte_identical_duplicate_files": inv["summary"]["byte_identical_duplicates"],
              "distinct_app_identities": len(ident), "distinct_app_ids": len(by_app), "distinct_vendor_groups_by_monitored_product": len(vendors_rep), "distinct_publishers_app_conf_author": len(publishers),
              "ta_sourcetype_names_distinct_incl_patterns": len(distinct_st), "ta_sourcetype_names_literal": len(literal), "ta_sourcetype_patterns": len(distinct_st) - len(literal),
              "catalog_vendors": len(vendors), "catalog_sourcetypes": len(rows), "catalog_products": len({(r["catalog_vendor"], r["catalog_product"]) for r in rows}),
              "match_types": dict(Counter(r["match_type"] for r in rows)), "naming_conflicts": sum(r["naming_conflict"] for r in rows),
              "exact_with_payload_conflict": sum(1 for r in rows if r["match_type"] == "exact" and any(x.startswith("payload") for x in r["conflicts"])),
              "exact_with_routing_conflict": sum(1 for r in rows if r["match_type"] == "exact" and any(x.startswith("routing") for x in r["conflicts"])),
              "format_verification": dict(Counter(r["format_verification"].split(" ")[0] for r in rows)), "generators_valid": sum(r["generator_valid"] for r in rows),
              "generators_valid_exact": sum(1 for r in rows if r["match_type"] == "exact" and r["generator_valid"]), "sample_backed": sum(1 for r in rows if r["sample_status"] != "NONE"),
              "live_verified": sum(1 for r in rows if r["live_verification"].startswith("SPLUNK_VERIFIED")), "catalog_sourcetypes_without_covering_package": sum(1 for r in rows if r["match_type"] == "none"),
              "catalog_sourcetypes_not_defined_by_any_package": sum(1 for r in rows if r["match_type"] != "exact"), "ta_sourcetypes_absent_from_netspout": len(absent),
              "ingestion_support_exact_rows": dict(Counter(r["ingestion_support"] for r in rows if r["match_type"] == "exact"))}
    p4 = json.loads((ROOT / "docs/contracts/ta_backed_registry.json").read_text())
    p4_names = {r["canonical_sourcetype"] for r in p4["rows"] if r["netspout"] and r["netspout"]["match"] == "EXACT"}
    p4_files = {p["package"] for p in json.loads((EVID / "ta_inventory/packages.json").read_text())["packages"]}
    p5_names = {n for n in catnames for r in ta_index.get(n, []) if not r["pattern"] and any(f in p4_files for f in r["files"])}
    totals["reconciliation_with_phase4"] = {"phase4_exact_names_in_14_packages": len(p4_names), "phase5_catalog_names_defined_by_the_same_14_packages": len(p5_names), "equal": p4_names == p5_names,
                                            "note": "Phase 5 re-classifies names that an add-on only renames (legacy names) as naming conflicts, so its exact count is lower than the literal-name count"}
    assert totals["reconciliation_with_phase4"]["equal"], "Phase 5 package/catalog name overlap must reproduce the Phase 4 registry for the 14 packages"
    assert totals["live_verified"] == sum(1 for v in LIVE.values() if v.get("passed")), "live-verified count must equal the Phase 4 evidence"

    # ------------------------------------------------------------------ ingestion classification (per distinct app identity)
    ing = []
    for (aid, ver), e in sorted(ident.items()):
        ac = app_cls[(aid, ver)]
        sup, note = support_for(e, ac)
        ing.append({"app_id": aid, "version": ver, "label": e["label"], "vendor_group": e["vendor_group"], "package_type": e["package_type"] if "package_type" in e else None, "files": e["files"], "sourcetypes": len(e["sourcetypes"]),
                    "mechanisms_declared_in_config": ac["config_declared"], "mechanisms_only_mentioned_in_readme": ac["readme_mentions_only"], "categories": ac["categories"], "payload_shape": ac["payload_shape"],
                    "metric_definitions_in_package": ac["metric_definitions"], "metric_indexes_declared": e["metrics_signals"]["metric_indexes"], "netspout_delivery": sup, "netspout_delivery_note": note})

    # ------------------------------------------------------------------ top 10
    cand = defaultdict(list)
    for r in rows:     # pool: exact name, generator really produces events, not already verified, no naming/routing/payload conflict, not a flow/OTel/database intake
        if r["match_type"] == "exact" and r["generator_valid"] and not r["live_verification"].startswith("SPLUNK") and r["ingestion_support"] != "NOT_EMULATED" \
                and r["format_verification"] != "FORMAT_CONFLICT" and not any(x.startswith(("routing", "naming")) for x in r["conflicts"]) and (r["sample_replayable"] or r["generator_mode"] == "native"):
            cand[(r["catalog_vendor"], r["ta_app_id"])].append(r)
    short = []
    for (vid, app), rs in cand.items():
        fv = [r for r in rs if r["format_verification"] == "FORMAT_VERIFIED"]
        weak = [r for r in rs if r["format_verification"] in ("FORMAT_PARTIAL", "STRUCTURE_ONLY")]
        sup = [r for r in rs if r["ingestion_support"] == "SUPPORTED_DELIVERY"]
        sc = sum(r["scenarios"] for r in rs)
        e = ident[(app, rs[0]["package_version"])]
        risk = []
        if any(r["format_verification"] == "FORMAT_PARTIAL" for r in rs):
            risk.append("some sourcetypes emit fewer columns than the add-on lists")
        if any(r["format_verification"] == "STRUCTURE_ONLY" for r in rs):
            risk.append("JSON structure only; field names not yet compared to the add-on")
        if any(r["format_verification"].startswith("NOT_CHECKABLE") for r in rs):
            risk.append("the add-on defines no extraction rules to check against for some sourcetypes")
        if not sup:
            risk.append("the add-on's real input is an API/agent/script: NetSpout can only deliver the events over HEC")
        score = 4 * (1 if sup else 0) + 3 * min(len(fv), 3) + min(len(weak), 2) + 2 * (1 if any(r["sample_replayable"] for r in rs) else 0) + (1 if any(r["shipped_yaml_samples"] for r in rs) else 0) + min(sc, 40) / 10.0
        complexity = "Low" if sup and fv else ("Medium" if sup or fv else "High")
        short.append({"vendor_id": vid, "vendor": vendors[vid]["name"], "ta_app_id": app, "ta_label": e["label"], "package_version": rs[0]["package_version"], "package_file": rs[0]["package_files"][0], "score": round(score, 2),
                      "exact_sourcetypes_ready": [r["catalog_sourcetype"] for r in rs][:8], "exact_ready_count": len(rs), "format_verified_count": len(fv), "scenario_references": sc,
                      "shipped_yaml_sample": any(r["shipped_yaml_samples"] for r in rs), "ingestion": sorted({x for r in rs for x in (r["ta_ingestion"] or [])}), "delivery": "SUPPORTED_DELIVERY" if sup else "SUBSTITUTE_VIA_HEC",
                      "estimated_complexity": complexity, "risks": risk,
                      "evidence": "exact names defined at %s; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (%d FORMAT_VERIFIED, %d partial/structure-only)" % (rs[0]["evidence"][0] if rs[0]["evidence"] else "?", len(fv), len(weak))})
    short.sort(key=lambda x: (-x["score"], {"Low": 0, "Medium": 1, "High": 2}[x["estimated_complexity"]], x["vendor_id"]))
    OUT.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(short, 1):
        s["rank"] = i
    mism = {"naming_conflicts": [{"catalog": r["catalog_sourcetype"], "vendor": r["catalog_vendor"], "ta_candidate": r["canonical_ta_sourcetype"], "package": r["ta_app_id"], "evidence": r["evidence"]} for r in rows if r["naming_conflict"]],
            "payload_format_conflicts": [{"catalog": r["catalog_sourcetype"], "package": r["ta_app_id"], "detail": [x for x in r["conflicts"] if x.startswith("payload")], "format": r["format_detail"]} for r in rows if r["match_type"] == "exact" and any(x.startswith("payload") for x in r["conflicts"])],
            "routing_conflicts": [{"catalog": r["catalog_sourcetype"], "package": r["ta_app_id"], "detail": [x for x in r["conflicts"] if x.startswith("routing")]} for r in rows if any(x.startswith("routing") for x in r["conflicts"])],
            "unsupported_ingestion": [{"catalog": r["catalog_sourcetype"], "package": r["ta_app_id"], "support": r["ingestion_support"], "why": r.get("ingestion_note")} for r in rows if r["match_type"] == "exact" and r["ingestion_support"] in ("SUBSTITUTE_VIA_HEC", "NOT_EMULATED")],
            "catalog_without_package": [{"catalog": r["catalog_sourcetype"], "vendor": r["catalog_vendor"]} for r in rows if r["match_type"] == "none"],
            "ta_sourcetypes_absent_from_netspout_count": len(absent)}
    (OUT / "master_matrix.json").write_text(json.dumps({"summary": totals, "rows": rows}, indent=1) + "\n")
    flat = ["catalog_vendor", "catalog_vendor_name", "catalog_product", "catalog_sourcetype", "match_type", "ta_app_id", "package_version", "canonical_ta_sourcetype", "ta_sourcetype_role", "naming_conflict", "generator_tier", "generator_valid", "generator_mode",
            "sample_status", "sample_replayable", "ta_ingestion", "ingestion_support", "destination", "ta_destination", "format_verification", "live_verification", "conflicts", "evidence", "remediation"]
    with open(OUT / "master_matrix.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(flat)
        for r in rows:
            w.writerow([("; ".join(r[k]) if isinstance(r[k], list) else r[k]) for k in flat])
    (OUT / "vendor_coverage.json").write_text(json.dumps({"summary": totals, "vendors": vend}, indent=1) + "\n")
    vf = ["vendor_id", "vendor", "products", "catalog_sourcetypes", "downloaded_matching_addons", "exact_canonical_matches", "naming_conflicts", "payload_or_routing_conflicts", "valid_generators", "sample_backed", "live_verified", "specialized_ingestion_required", "main_blockers"]
    with open(OUT / "vendor_coverage.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(vf)
        for v in vend:
            w.writerow([("; ".join(v[k]) if isinstance(v[k], list) else v[k]) for k in vf])
    (OUT / "sourcetype_mismatches.json").write_text(json.dumps(mism, indent=1) + "\n")
    (OUT / "ingestion_classification.json").write_text(json.dumps(ing, indent=1) + "\n")
    (OUT / "top10_shortlist.json").write_text(json.dumps(short[:10], indent=1) + "\n")
    with open(OUT / "ta_sourcetype_index.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ta_sourcetype", "is_pattern", "app_id", "version", "role", "defined_in", "in_netspout_catalog"])
        for n in sorted(ta_index):
            for r in ta_index[n]:
                w.writerow([n, r["pattern"], r["app"], r["version"], r["role"], r["where"][0], n in catnames])
    pk = [{"filename": p["path"], "bytes": p["bytes"], "sha256": p["sha256"], "status": p["status"], "reason": p["reason"], "duplicate_of": p["duplicate_of"],
           "apps": [{"id": a["id"], "label": a["label"], "version": a["version"], "publisher": a.get("publisher"), "type": a.get("package_type"), "sourcetypes": len(a["sourcetypes"]), "dependencies": a["dependencies"]} for a in p["apps"]]} for p in inv["packages"]]
    (OUT / "package_inventory.json").write_text(json.dumps({"summary": inv["summary"], "packages": pk}, indent=1) + "\n")
    with open(OUT / "package_inventory.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["filename", "bytes", "sha256", "status", "duplicate_of", "app_ids", "versions", "display_names", "publishers", "package_types", "declared_sourcetypes"])
        for p in pk:
            w.writerow([p["filename"], p["bytes"], p["sha256"], p["status"], p["duplicate_of"] or "", "; ".join(a["id"] for a in p["apps"]), "; ".join(str(a["version"]) for a in p["apps"]), "; ".join(str(a["label"]) for a in p["apps"]),
                        "; ".join(str(a["publisher"]) for a in p["apps"]), "; ".join(str(a["type"]) for a in p["apps"]), sum(a["sourcetypes"] for a in p["apps"])])
    print(json.dumps(totals, indent=1))
    print("pool", len(short)); print("top10:", [(s["rank"], s["vendor_id"], s["ta_app_id"], s["score"], s["exact_ready_count"], s["format_verified_count"], s["delivery"], s["estimated_complexity"]) for s in short[:14]])
    print("vendor groups:", sorted(vendors_rep)[:200])


if __name__ == "__main__":
    main()
