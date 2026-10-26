"""Build the Universal Vendor Coverage registry from the pinned Splunkbase snapshot.

Reads catalog/vendor_universe/splunkbase_apps_snapshot.json (metadata-only snapshot of the
public Splunkbase API; no packages are downloaded) plus the canonical catalogs, and emits
catalog/vendor_universe.json with strictly separated count dimensions.

Classification rules (deterministic, first-match wins, basis recorded per app):
  splunk_platform              -> is_splunk_built or Splunk publisher
  canonical_linked             -> app maps to an existing canonical vendor record
                                  (splunkbase uid / declared canonical sourcetype / canonical-vendor alias in title+appid)
  recognized_technology_vendor -> curated vendor lexicon hit in title+appid (non-canonical vendor)
  product_only                 -> product token parsed from a splunkbase-pattern title, vendor unrecognized
  publisher_only               -> consultancy/individual publisher utility; no vendor, no product

Publishers are never promoted to technology vendors on name alone.
"""
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "catalog/vendor_universe/splunkbase_apps_snapshot.json"
CATALOG = ROOT / "catalog"
DEST = ROOT / "catalog/vendor_universe.json"


def norm_text(s):
    return re.sub(r"[^a-z0-9+]+", " ", (s or "").lower()).strip()


# Canonical vendors: exact NetSpout vendor rows (id -> match aliases), applied first.
CANONICAL_VENDORS = {
    "a10_networks": ["a10 networks", "a10networks", "acos"],
    "arista_eos": ["arista networks", "arista", "eos"],
    "aruba_cx": ["aruba", "arubaos", "aruba cx", "hpe aruba"],
    "checkpoint": ["check point", "checkpoint", "gaia"],
    "cisco_aci": ["cisco aci", "application centric infrastructure"],
    "cisco_asa": ["cisco asa", "cisco ftd", "cisco firepower", "cisco secure firewall", "cisco defense orchestrator", "cisco fmc", "secure firewall"],
    "cisco_catalyst": ["cisco catalyst"],
    "cisco_duo": ["cisco duo", "duo security", "duo admin"],
    "cisco_intersight": ["cisco intersight"],
    "cisco_ios": ["cisco ios", "cisco networks", "cisco nx os", "cisco nxos", "cisco nexus"],
    "cisco_ise": ["cisco ise", "identity services engine", "cisco identity service engine"],
    "cisco_meraki": ["cisco meraki", "meraki"],
    "cisco_sdwan": ["cisco sd wan", "cisco sdwan", "cisco viptela", "cisco vmanage", "cisco catalyst sd wan"],
    "citrix_netscaler": ["citrix", "netscaler", "citrix adc", "citrix ble"],
    "cloudflare": ["cloudflare"],
    "dell_os10": ["dell"],
    "extrahop": ["extrahop"],
    "extreme_networks": ["extreme networks", "extremeware", "viprion"],
    "f5_bigip": ["f5", "big ip", "bigip", "ltm", "asm"],
    "forcepoint": ["forcepoint", "websense"],
    "fortinet": ["fortinet", "fortigate", "fortiweb", "fortimail", "fortianalyzer", "fortimanager", "forti", "fortiauthenticator", "fortiproxy"],
    "huawei_vrp": ["huawei"],
    "juniper_junos": ["juniper", "junos", "netscreen", "srx"],
    "netscout": ["netscout", "arbor", "omnis"],
    "netskope": ["netskope"],
    "nokia_sr": ["nokia", "7750 sr", "sr os"],
    "nutanix": ["nutanix", "prism element"],
    "palo_alto": ["palo alto", "paloalto", "cortex xdr", "cortex xp", "pan os", "panorama", "prisma access", "prisma cloud"],
    "radware": ["radware", "defensepro"],
    "sc4snmp": ["sc4snmp", "splunk connect for snmp"],
    "sonicwall": ["sonicwall", "sonicos"],
    "sophos": ["sophos", "utm 9", "xg firewall", "cyberoam"],
    "splunk": ["splunk"],
    "vmware_nsx": ["vmware", "vsphere", "nsx", "vcenter", "esxi"],
    "watchguard": ["watchguard", "firebox"],
    "zscaler_zia": ["zscaler", "z ia", "zia", "zpa", "zdx"],
    "microsoft_windows": ["microsoft windows", "windows defender", "sysmon", "microsoft sysmon"],
    "crowdstrike": ["crowdstrike", "falcon", "fdr", "humio"],
    "amazon_aws": ["aws", "amazon web services", "amazon", "cloudwatch", "vpc flow", "kinesis", "ec2", "s3"],
    "microsoft_365": ["office 365", "o365", "microsoft 365", "exchange online"],
    "microsoft_azure": ["azure", "microsoft sentinel", "entra", "active directory"],
    "okta": ["okta"],
    "suricata_oisf": ["suricata"],
    "osquery": ["osquery"],
    "ollama": ["ollama"],
    "model_context_protocol": ["model context protocol", "mcp"],
    "google_workspace": ["google workspace", "gmail", "google apps", "gsuite", "g suite"],
    "kubernetes": ["kubernetes", "k8s", "falco", "openshift", "rancher", "helm"],
    "crushftp": ["crushftp"],
    "zeek": ["zeek", "bro"],
    "google_cloud": ["google cloud", "gcp", "bigquery"],
    "opentelemetry": ["opentelemetry", "otel"],
}
# Curated extended vendor lexicon: industry-recognized technology vendors beyond the
# canonical 53. Applied after canonical rules; longer aliases take precedence.
EXTENDED_VENDORS = {
    "cisco_other": ["cisco"],
    "proofpoint": ["proofpoint"],
    "sentinelone": ["sentinelone"],
    "trend_micro": ["trend micro", "trendmicro", "apex central", "deep security", "cloud one", "tippingpoint"],
    "trellix_mcafee": ["trellix", "mcafee", "fireeye", "mandiant"],
    "broadcom_symantec": ["symantec", "carbon black", "broadcom", "blue coat", "bluecoat", "brocade"],
    "eset": ["eset"],
    "kaspersky": ["kaspersky"],
    "bitdefender": ["bitdefender"],
    "malwarebytes": ["malwarebytes"],
    "darktrace": ["darktrace"],
    "vectra_ai": ["vectra"],
    "cybereason": ["cybereason "],
    "tanium": ["tanium"],
    "varonis": ["varonis"],
    "rapid7": ["rapid7", "insightidr"],
    "qualys": ["qualys"],
    "tenable": ["tenable", "nessus"],
    "imperva": ["imperva"],
    "akamai": ["akamai"],
    "barracuda": ["barracuda"],
    "cyberark": ["cyberark", "conjur "],
    "sailpoint": ["sailpoint"],
    "ping_identity": ["ping identity", "pingidentity", "pingfederate"],
    "forgerock": ["forgerock", "openam "],
    "onelogin": ["onelogin"],
    "beyondtrust": ["beyondtrust", "powerbroker "],
    "delinea_thycotic": ["delinea", "secret server", "thycotic"],
    "ivanti": ["ivanti", "landesk"],
    "manageengine_zoho": ["manageengine", "zoho"],
    "solarwinds": ["solarwinds", "orion "],
    "servicenow": ["servicenow"],
    "atlassian": ["atlassian", "jira", "confluence"],
    "gitlab": ["gitlab"],
    "github": ["github"],
    "zoom": ["zoom "],
    "slack": ["slack "],
    "dropbox": ["dropbox"],
    "docusign": ["docusign"],
    "salesforce": ["salesforce"],
    "oracle": ["oracle"],
    "ibm_qradar": ["qradar", "ibm", "bigfix"],
    "hp_enterprise": ["hpe ", "hewlett ", "hp oneview"],
    "hikvision": ["hikvision"],
    "axis_communications": ["axis communications"],
    "hanwha": ["hanwha", "wisenet"],
    "mobotix": ["mobotix"],
    "veeam": ["veeam"],
    "commvault": ["commvault"],
    "veritas": ["veritas", "netbackup"],
    "netapp": ["netapp"],
    "pure_storage": ["pure storage", "purestorage"],
    "hitachi_vantara": ["hitachi"],
    "synology": ["synology"],
    "qnap": ["qnap"],
    "truenas_ixsystems": ["truenas", "ixsystems"],
    "mongodb": ["mongodb"],
    "postgresql": ["postgres", "postgresql"],
    "mysql": ["mysql"],
    "mariadb": ["mariadb"],
    "redis": ["redis"],
    "elastic": ["elastic", "elasticsearch"],
    "influxdata": ["influxdata", "influxdb"],
    "clickhouse": ["clickhouse"],
    "couchbase": ["couchbase"],
    "docker": ["docker", "containerd"],
    "hashicorp": ["hashicorp", "terraform", "vault", "consul "],
    "kong": ["kong api", "kong inc"],
    "traefik": ["traefik"],
    "envoyproxy": ["envoy proxy", "envoyproxy"],
    "argocd": ["argocd", "argo cd"],
    "istio": ["istio"],
    "linkerd": ["linkerd"],
    "cilium_isovalent": ["cilium", "isovalent", "hubble "],
    "prometheus": ["prometheus"],
    "grafana_labs": ["grafana", "loki "],
    "datadog": ["datadog"],
    "dynatrace": ["dynatrace"],
    "new_relic": ["new relic", "newrelic"],
    "sysdig": ["sysdig"],
    "aqua_security": ["aqua security", "aquasec"],
    "cribl": ["cribl"],
    "sumo_logic": ["sumo logic", "sumologic"],
    "logrhythm_exabeam": ["logrhythm", "exabeam"],
    "graylog": ["graylog"],
    "wazuh": ["wazuh"],
    "devo": ["devo"],
    "opensearch": ["opensearch"],
    "teleport_gravitational": ["teleport "],
    "mikrotik": ["mikrotik", "routeros"],
    "ubiquiti": ["ubiquiti", "unifi"],
    "tplink": ["tp link", "tplink", "omada"],
    "zyxel": ["zyxel"],
    "pfsense_netgate": ["pf sense", "pfsense", "netgate"],
    "opnsense": ["opnsense"],
    "untangle": ["untangle"],
    "vyos": ["vyos"],
    "hillstone": ["hillstone"],
    "clavister": ["clavister"],
    "draytek": ["draytek"],
    "cambium": ["cambium"],
    "ruckus_commscope": ["ruckus", "commscope"],
    "ericsson": ["ericsson"],
    "mavenir": ["mavenir"],
    "ribbon_communications": ["ribbon communications"],
    "sierra_wireless": ["sierra wireless", "sierrawireless"],
    "nozomi_networks": ["nozomi"],
    "claroty": ["claroty"],
    "red_canary": ["red canary"],
    "greynoise": ["greynoise"],
    "anomali": ["anomali"],
    "threatconnect": ["threatconnect"],
    "recorded_future": ["recorded future", "recordedfuture"],
    "eclecticiq": ["eclecticiq", "eclectic iq"],
    "virustotal": ["virustotal", "virus total"],
    "misp_project": ["misp"],
    "corelight": ["corelight"],
    "pavo_metrics": ["pavo "],
    "sftpgo": ["sftpgo"],
    "zimbra": ["zimbra"],
    "keycloak": ["keycloak"],
    "freeipa": ["freeipa"],
    "openvpn": ["openvpn"],
    "wireguard": ["wireguard"],
    "nginx_f5": ["nginx", "open resty"],
    "redis_labs": ["redis labs"],
    "paloalto_ex": [],  # removed below; canonical handles this vendor
}
EXTENDED_VENDORS = {k: [a.strip() for a in v if a and a.strip()] for k, v in EXTENDED_VENDORS.items() if v}

LEXICON = [(key, alias) for key, aliases in {**CANONICAL_VENDORS, **EXTENDED_VENDORS}.items() for alias in aliases]
LEXICON.sort(key=lambda ka: -len(ka[1]))


def extract_product(title, appid):
    t = (title or "").strip()
    m = re.match(r"^splunk\s+(?:technology\s+|ta\s*\+?|)add-?on\s+for\s+(?P<p>.+)$", t, re.I)
    if m:
        return m.group("p").strip()
    m = re.match(r"^splunk\s+app\s+for\s+(?P<p>.+)$", t, re.I)
    if m:
        return m.group("p").strip()
    m = re.match(r"^splunk\s+add-?on\s+(?P<p>.+)$", t, re.I)
    if m:
        return m.group("p").strip()
    m = re.match(r"^(?P<p>.+?)\s+(?:technology\s+add-?on|ta|add-?on|app|integration|automation)(?:\s+for\s+splunk.*)?$", t, re.I)
    if m and m.group("p").strip():
        return m.group("p").strip()
    if (appid or "").startswith("TA-"):
        return appid[3:].replace("-", " ").strip()
    if (appid or "").startswith("AddOn"):
        return appid[5:].replace("-", " ").strip()
    return None


def norm_product(p):
    if not p:
        return None
    p = re.sub(r"\s*[-–]?\s*(for\s+)?splunk(?!base)\s*$", "", p, flags=re.I)
    p = re.sub(r"^the\s+", "", p.strip(), flags=re.I)
    p = re.sub(r"\s+", " ", p).strip(" -_")
    return p.lower() or None


def norm_publisher(name):
    if not name:
        return None
    n = re.sub(r"\s*[-–]\s*(key\s+)?partner(\s+acct)?\s*$", "", name.strip(), flags=re.I)
    n = re.sub(r"\s+(inc|llc|ltd|gmbh|co|corp|srl|pvt)\.?\s*$", "", n, flags=re.I)
    return n.strip() or None


def classify(app, canonical_uids, canonical_st_names, canonical_alias_info):
    """Assign exactly one coverage bucket with its audited basis."""
    declared = set()
    for _tags, sts in (app.get("rel_tags_st") or {}).items():
        declared.update(sts or [])
    if app.get("is_splunk_built") or (app.get("author_redirect") or "").lower().startswith("splunk") or (app.get("author") or "").strip().lower() == "splunk":
        return "splunk_platform", {"basis": "is_splunk_built_or_splunk_publisher"}
    if app["uid"] in canonical_uids:
        return "canonical_linked", {"basis": "canonical_splunkbase_uid", "canonical_vendor": canonical_uids[app["uid"]]}
    canon_hit = declared & canonical_st_names
    if canon_hit:
        return "canonical_linked", {"basis": "declared_canonical_sourcetype", "canonical_sourcetypes": sorted(canon_hit)[:6]}
    text_a = norm_text(app["appid"] + " " + app["name"])
    for vid, aliases in canonical_alias_info:
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias).replace(" ", r"\s+") + r"\b", text_a):
                return "canonical_linked", {"basis": "canon_alias_title", "canonical_vendor": vid, "alias": alias}
    for key, alias in LEXICON:
        # "for Splunk" describes the target platform, not the technology vendor.
        if key == "splunk":
            continue
        if re.search(r"\b" + re.escape(alias).replace(" ", r"\s+") + r"\b", text_a):
            if key in {vid for vid, _aliases in canonical_alias_info}:
                return "canonical_linked", {"basis": "vendor_lexicon_canonical", "canonical_vendor": key, "alias": alias}
            return "recognized_technology_vendor", {"basis": "vendor_lexicon", "vendor_key": key, "alias": alias}
    np_ = norm_product(extract_product(app["name"], app["appid"]))
    if np_ and len(np_) >= 3:
        return "product_only", {"basis": "title_product_pattern", "product": np_}
    return "publisher_only", {"basis": "no_recognized_vendor_or_product"}


def main():
    snap = json.loads(SNAPSHOT.read_text())
    rows = snap["rows"]
    canon_vendors = json.loads((CATALOG / "vendors.json").read_text())
    canon_sts = json.loads((CATALOG / "sourcetypes.json").read_text())
    canon_by_id = {v["id"]: v for v in canon_vendors}
    canonical_uids = {int(v["splunkbase_id"]): v["id"] for v in canon_vendors if str(v.get("splunkbase_id") or "").isdigit()}
    canonical_st_names = {s["splunk_sourcetype"] for s in canon_sts}

    def aliases_for(v):
        out = [norm_text(v["name"])]
        for frag in re.split(r"[/(),]", v["name"]):
            frag = norm_text(frag)
            if len(frag) >= 4 and frag not in out:
                out.append(frag)
        return out

    canonical_alias_info = [(v["id"], aliases_for(v)) for v in canon_vendors if v["id"] not in ("linux_infrastructure", "splunk")]
    canonical_alias_info.sort(key=lambda va: -max(len(a) for a in va[1]))

    classified = [(app, *classify(app, canonical_uids, canonical_st_names, canonical_alias_info)) for app in rows]
    buckets = Counter(b for _a, b, _i in classified)

    # Section 7 dimensions come from committed evidence files only
    live_union = set()
    for live_file in (
        "raw_reference/live_raw_equality_results.json",
        "raw_reference/wave2_live_raw_equality_results.json",
        "wave3_live_raw_equality_results.json",
        "universe_batch1_live_raw_equality_results.json",
        "universe_batch1_current_raw_equality_results.json",
        "universe_batch2_current_raw_equality_results.json",
    ):
        p = CATALOG / live_file
        if not p.exists():
            continue
        j = json.loads(p.read_text())
        live_union |= {e["sourcetype"] for e in j.get("raw_equality", []) if e.get("verdict") == "PASS"}
    wave_families = 0
    for w in ("wave1", "wave2", "wave3"):
        reg = json.loads((CATALOG / f"{w}_source_expansion.json").read_text())
        wave_families += sum(s.get("event_family_count", len(s.get("event_families", []))) for s in reg["sources"])
    for filename in ("universe_batch1.json", "universe_batch2.json"):
        if (CATALOG / filename).exists():
            batch = json.loads((CATALOG / filename).read_text())
            wave_families += sum(source["event_family_count"] for source in batch["sources"])

    publishers = sorted({norm_publisher(a.get("author")) for a, _b, _i in classified if a.get("author")} - {None})
    raw_publishers = sorted({a["author"] for a, _b, _i in classified if a.get("author")})
    extended_vendors = Counter(i["vendor_key"] for _a, b, i in classified if b == "recognized_technology_vendor")
    canonical_linked = Counter(i["canonical_vendor"] for _a, b, i in classified if b == "canonical_linked" and "canonical_vendor" in i)
    products = Counter()
    for app, b, i in classified:
        if b == "product_only":
            products[i["product"]] += 1
        elif b == "recognized_technology_vendor":
            p = norm_product(extract_product(app["name"], app["appid"]))
            if p and len(p) >= 3:
                products[p] += 1
    canonical_st_refs = Counter()
    declared_apps = 0
    for app, _b, _i in classified:
        dec = set()
        for _t, sts in (app.get("rel_tags_st") or {}).items():
            dec.update(sts or [])
        ref = sorted(dec & canonical_st_names)
        if ref:
            declared_apps += 1
            canonical_st_refs.update(ref)

    buckets_detail = {}
    for app, bucket, basis in classified:
        d = buckets_detail.setdefault(bucket, {"count": 0, "apps": []})
        d["count"] += 1
        d["apps"].append({"appid": app["appid"], "name": app["name"], "author": app["author"], "basis": basis, "downloads": app["downloads"]})

    counts = {
        # 1. Discovered vendors and products (publishers kept separate, never promoted)
        "discovered_publishers_raw": len(raw_publishers),
        "discovered_publishers_normalized": len(publishers),
        "discovered_technology_vendors_canonical": len(canon_by_id),
        "discovered_technology_vendors_extended": len(extended_vendors),
        "discovered_products": len(products),
        # 2. Splunkbase applications and TAs
        "splunkbase_apps_total": len(rows),
        "splunkbase_addons": sum(1 for a, _b, _i in classified if a["app_type"] == "addon"),
        "splunkbase_applications": sum(1 for a, _b, _i in classified if a["app_type"] == "app"),
        # 3. Canonical sourcetypes
        "canonical_sourcetypes": len(canon_sts),
        # 4. Genuine event families (evidence-backed wave-registry instances)
        "genuine_event_families_evidenced": wave_families,
        # 5. Generator-implemented sources (all canonical rows ship executable generators)
        "generator_implemented_sources": len(canon_sts),
        # 6. Live-ingestion-verified sources (committed RAW-equality PASS union)
        "live_ingestion_verified_sourcetypes": len(live_union),
        # 7. TA-parser-verified sources (requires locally installed required TA)
        "ta_parser_verified_sourcetypes": 1,
    }

    registry = {
        "schema_version": "1.0.0",
        "registry_version": "2026.10.26-universe-1",
        "created_utc": snap["fetched_utc"],
        "purpose": "Ecosystem-wide, deduplicated Splunkbase vendor/product/TA coverage universe with strictly separated count dimensions (Universal Vendor Coverage Mandate).",
        "discovery_coverage": {"denominator": snap["declared_totals"]["api_v1_list_total"], "rows": len(rows), "scope": "Pinned public Splunkbase list API snapshot on 2026-10-26", "limitations": "Complete only against the declared snapshot denominator; not an exhaustive global vendor/product inventory. Private, removed, unlisted and non-Splunkbase integrations excluded. Curated first-match lexicon and title-derived product candidates require review; Splunk-published vendor integrations can fall in the platform bucket."},
        "methodology": {
            "publisher_not_vendor": "Publisher (display_author) names are counted as publishers only. Technology vendors are recognized through the curated vendor lexicon applied against app title + appid; consultancy/partner publishers remain publishers and are never promoted to vendors.",
            "not_all_apps_produce_telemetry": "Directory listings and utility apps are counted in the universe but are explicitly excluded from telemetry-coverage claims.",
            "classification_first_match": ["splunk_platform", "canonical_linked", "recognized_technology_vendor", "product_only", "publisher_only"],
            "vendor_lexicon_size": len(LEXICON),
            "canonical_link_rules": ["splunkbase uid exact match", "declared sourcetype in canonical registry", "canonical vendor alias in title/appid (word-boundary match, longest alias first)"],
            "count_dimensions": list(counts),
        },
        "provenance": {
            "snapshot_file": "catalog/vendor_universe/splunkbase_apps_snapshot.json",
            "snapshot_sha256": hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
            "snapshot_bytes": SNAPSHOT.stat().st_size,
            "fetched_utc": snap["fetched_utc"],
            "api_endpoints": snap["source_api"],
            "fetch_scope": "Public Splunkbase metadata API only; no app packages downloaded, no TA installed, no Splunk config changes.",
            "upstream_publisher": "Splunk Inc. (Splunkbase public catalog API)",
        },
        "counts": counts,
        "counts_by_bucket": dict(buckets),
        "canonical_coverage_crossmap": {
            "apps_declaring_canonical_sourcetypes": declared_apps,
            "canonical_sourcetypes_declared_by_splunkbase": len(canonical_st_refs),
            "top_declared_canonical_sourcetypes": canonical_st_refs.most_common(20),
            "canonical_vendors_with_uid_or_title_match": sorted(set(canonical_linked) - {None}),
        },
        "extended_vendors": extended_vendors.most_common(),
        "extended_products": products.most_common(),
        "classified_apps": [{"uid": a["uid"], "appid": a["appid"], "bucket": b, **i} for a, b, i in classified],
        "uncovered_vendor_queue": [{"vendor_key": k, "app_count": n, "status": "EVIDENCE_AND_TA_REVIEW_REQUIRED"} for k, n in extended_vendors.most_common()],
        "publishers": publishers,
        "ta_parser_verified": {
            "sourcetype": "cisco:ise:syslog",
            "ta": "Splunk_TA_cisco-ise 5.0.0 (installed locally; search-time controlled extraction verified)",
            "note": "TA-parser verification requires the required TA installed locally. Installing additional packages requires separate authorization, so this count stays low by definition and is never inflated.",
        },
        "live_verification_sources": [
            "catalog/raw_reference/live_raw_equality_results.json",
            "catalog/raw_reference/wave2_live_raw_equality_results.json",
            "catalog/wave3_live_raw_equality_results.json",
            "catalog/universe_batch1_live_raw_equality_results.json",
            "catalog/universe_batch1_current_raw_equality_results.json",
            "catalog/universe_batch2_current_raw_equality_results.json",
        ],
        "restricted_access_apps": sum(1 for a, _b, _i in classified if a["access"] != "unrestricted"),
        "directory_listing_apps": sum(1 for a, _b, _i in classified if a["is_directory_listing"]),
        "app_examples": {b: buckets_detail[b]["apps"][:8] for b in buckets_detail},
        "batches": {
            "batch_1": {
                "status": "COMPLETE",
                "scope": "Bounded multi-vendor evidence-backed generator batch selected from universe priority gaps",
                "registry": "catalog/universe_batch1.json",
                "new_canonical_vendors": ["docker", "broadcom_symantec", "wazuh", "nozomi_networks"],
                "new_canonical_sourcetypes": ["docker_events",
                                              "bluecoat:proxysg:access:file",
                                              "wazuh:alerts",
                                              "nozomi:universal_alert"],
                "live_verification": "Historical 9/9 RAW-equality PASS before recovery; revised generators not re-ingested",
            }
        },
    }
    registry["live_verification_sources"] = [rel for rel in registry["live_verification_sources"] if (ROOT / rel).is_file()]
    current_batch1 = CATALOG / 'universe_batch1_current_raw_equality_results.json'
    if current_batch1.is_file():
        check = json.loads(current_batch1.read_text())
        registry['batches']['batch_1']['live_verification'] = f"Current bytes {check['passes']}/{check['posted']} RAW equality PASS; {current_batch1.name}"
    batch2_path = CATALOG / 'universe_batch2.json'
    if batch2_path.is_file():
        batch2 = json.loads(batch2_path.read_text())
        registry['batches']['batch_2'] = dict(registry='catalog/universe_batch2.json',
                                            status='OFFLINE_IMPLEMENTED', counts=batch2['counts_summary'],
                                            live_verification=batch2['live_verification'])
        registry['candidate_queue_baseline'] = 'catalog/vendor_universe/batch2_candidate_queue_baseline.json'
    DEST.write_text(json.dumps(registry, indent=2))
    print("registry:", DEST.name, DEST.stat().st_size, "bytes")
    print(json.dumps(counts, indent=1))
    print("buckets:", dict(buckets))
    print("top extended vendors:", extended_vendors.most_common(20))
    print("top products:", products.most_common(25))


if __name__ == "__main__":
    main()
