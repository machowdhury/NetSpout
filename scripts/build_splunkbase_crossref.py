#!/usr/bin/env python3
"""Splunkbase add-on coverage audit against the PulseForge registry.

  snapshot   Preserve the user-supplied addon.csv rows (it is an Excel workbook saved with a .csv extension: ONE column, "Add-on Name") with
             provenance, join each name to its Splunkbase UID through splunkbase_addons.csv (Title -> UID; both files are inputs, neither is
             invented), and enrich with the public Splunkbase v1 API. Writes docs/verification/evidence/splunkbase/addon_snapshot.json.
  crossref   Offline. Join the snapshot to the pinned Splunkbase apps snapshot (catalog/vendor_universe/, fetched 2026-10-26, which carries each
             release's DECLARED sourcetypes in rel_tags_st) and to the PulseForge registry. Writes docs/verification/evidence/splunkbase/crossref.json and
             docs/verification/pulseforge_splunkbase_crossref{,_sourcetypes}.csv.

Evidence rules: a sourcetype is "declared" only if Splunkbase lists it for a release; nothing is inferred from a product name. A declared
sourcetype is a MISSING_SOURCETYPE only when the declaring app's vendor/product already exists in PulseForge; otherwise the gap is reported at
vendor/product level (MISSING_VENDOR_PRODUCT) and is not counted as a sourcetype gap. Role labels are keyword heuristics and say so.

Usage: build_splunkbase_crossref.py snapshot [--from-cache RAW.json] | crossref
"""
import argparse
import csv
import hashlib
import json
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
V = ROOT / "docs" / "verification"
HOME = Path.home() / "Downloads"
EVID = V / "evidence" / "splunkbase"
SNAP = EVID / "addon_snapshot.json"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
norm = lambda s: re.sub(r"\s+", " ", (s or "").strip().casefold())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_xlsx_column(path):
    """addon.csv is an .xlsx (zip) container; read sheet1 with the standard library only."""
    z = zipfile.ZipFile(path)
    sst = ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
    rows = []
    for r in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).find("m:sheetData", NS).findall("m:row", NS):
        c = r.find("m:c", NS)
        v = c.find("m:v", NS) if c is not None else None
        rows.append(sst[int(v.text)] if (c is not None and c.get("t") == "s" and v is not None) else (v.text if v is not None else None))
    core = ET.fromstring(z.read("docProps/core.xml"))
    meta = {t.tag.split("}")[1]: t.text for t in core}
    return rows[0], rows[1:], meta


# ----------------------------------------------------------------------------------------------------------------- snapshot
def snapshot(args):
    import urllib.request
    src = Path(args.addon)
    header, names, meta = read_xlsx_column(src)
    uid_map = {norm(r["Title"]): r["UID"] for r in csv.DictReader(open(args.uids, newline="", encoding="utf-8-sig"))}
    cache = {str(o["uid"]): o for o in json.loads(Path(args.from_cache).read_text())
             if o.get("app") and "error" not in o["app"] and isinstance(o.get("releases"), list) and o["releases"]} if args.from_cache else {}

    def get(url):
        for attempt in range(6):
            try:
                return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "netspout-coverage-audit"}), timeout=40).read())
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(min(20 * (attempt + 1), 120))
                    continue
                return {"error": "HTTP %s" % e.code}
            except Exception:
                time.sleep(3)
        return {"error": "unavailable"}

    apps = []
    for i, name in enumerate(names, 1):
        uid = uid_map.get(norm(name))
        entry = {"csv_row": i + 1, "csv_name": name, "uid": uid, "uid_source": "splunkbase_addons.csv (exact Title match)" if uid else None, "api_v1": None}
        if uid:
            cached = cache.get(uid)  # cache entries are a prior run of this same v1 fetch
            app, rel = (cached["app"], cached["releases"]) if cached else (get(f"https://splunkbase.splunk.com/api/v1/app/{uid}/?include=support,documentation,release"),
                                                                          get(f"https://splunkbase.splunk.com/api/v1/app/{uid}/release/"))
            if "error" not in app and isinstance(rel, list) and rel:
                latest = rel[0]
                entry["api_v1"] = {"appid": app.get("appid"), "title": app.get("title"), "type": app.get("type"), "license_name": app.get("license_name"),
                                   "description": app.get("description"), "download_count": app.get("download_count"), "archive_status": app.get("archive_status"),
                                   "cloud_compatible": app.get("cloud_compatible"), "support": app.get("support"), "documentation": app.get("documentation"),
                                   "created_time": app.get("created_time"), "updated_time": app.get("updated_time"), "url": app.get("path"),
                                   "latest_release": {"version": latest.get("name"), "product_versions": latest.get("product_versions"), "cim_versions": latest.get("CIM_versions"),
                                                      "published": latest.get("published_datetime"), "filename": latest.get("filename")}}
            else:
                entry["api_v1"] = {"error": app.get("error") or "release list unavailable"}
        apps.append(entry)
    doc = {"schema_version": "1.0", "source": {"file": src.name, "sha256": sha256(src), "actual_format": "Excel workbook (xlsx zip) saved with a .csv extension",
                                              "columns": [header], "data_rows": len(names), "workbook_created_utc": meta.get("created"), "workbook_modified_utc": meta.get("modified"),
                                              "export_date": "UNKNOWN: the workbook records its own save time only (above), not when Splunkbase was exported",
                                              "uid_join_file": Path(args.uids).name, "uid_join_file_sha256": sha256(args.uids)},
           "api": {"endpoint": "https://splunkbase.splunk.com/api/v1/app/{uid}/ and /release/ (public metadata, no login, no package download)",
                   "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")},
           "apps": apps}
    SNAP.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = sum(1 for a in apps if a["api_v1"] and "error" not in a["api_v1"])
    print(json.dumps({"rows": len(apps), "uid_joined": sum(1 for a in apps if a["uid"]), "api_enriched": ok, "api_missing": len(apps) - ok}))


# ----------------------------------------------------------------------------------------------------------------- crossref
PROTOCOL_SUPPORTED = ["syslog", "hec", "otlp", "snmp", "netflow v9", "ipfix", "gnmi"]  # native in PulseForge (see docs/NATIVE_*.md, gates 11-13)
ROLE_RULES = [
    ("NETWORK_PROTOCOL", r"\bsflow\b|\bj-?flow\b|\bnetflow\b|\bipfix\b|\bsnmp\b|\bgnmi\b|telemetry streaming"),
    ("METRICS", r"\bmetrics?\b|prometheus|telegraf|statsd|opentelemetry|\botel\b"),
    ("SECURITY_CONTENT", r"content pack|correlation search|analytic stor|detections?\b"),
    ("API_COLLECTOR", r"\bapis?\b|rest api|\bodata\b|graphql|webhook|polls?\b|modular input|collects? (data|events|logs) from"),
]
UNSUPPORTED_PROTOCOL = r"\bsflow\b|\bj-?flow\b|netflow v?5\b"


def roles_for(text):
    t = text.lower()
    found = [name for name, pat in ROLE_RULES if re.search(pat, t)]
    return found or ["PARSES_EXISTING_TELEMETRY"]


def crossref(args):
    snap = json.loads(SNAP.read_text())
    pinned = json.loads((CATALOG / "vendor_universe" / "splunkbase_apps_snapshot.json").read_text())
    pinned_by = {str(r["uid"]): r for r in pinned["rows"]}
    classified = {str(x["uid"]): x for x in json.loads((CATALOG / "vendor_universe.json").read_text())["classified_apps"]}
    uncovered = {q["vendor_key"]: q for q in json.loads((CATALOG / "vendor_universe.json").read_text())["uncovered_vendor_queue"]}
    cat = json.loads((CATALOG / "sourcetypes.json").read_text())
    vendors = {v["id"]: v for v in json.loads((CATALOG / "vendors.json").read_text())}
    cov = {r["sourcetype"]: r for r in csv.DictReader(open(V / "pulseforge_sourcetype_coverage.csv"))}
    lab = json.loads((V / "evidence" / "ta_validation" / "windows_sysmon.json").read_text())
    ta_checked = {e["sourcetype_emitted"] for e in lab["events"] if e["variant"] == "B" and e["indexed"]}
    # canonical lookup: exact, case-insensitive, catalog alias
    exact = {r["splunk_sourcetype"]: r for r in cat}
    ci = {r["splunk_sourcetype"].lower(): r for r in cat}
    alias = {}
    for r in cat:
        for a in r.get("aliases", []) + r.get("deprecated_aliases", []):
            alias.setdefault(a, r)
    # scenario index: which non-runnable scenarios name a sourcetype (these are the unblock targets)
    scen_by_st = defaultdict(set)
    for s in json.loads((CATALOG / "scenarios.json").read_text()):
        for st in s.get("sourcetypes", []):
            scen_by_st[st].add(s["id"])
    for c in json.loads((CATALOG / "scenario_candidates.json").read_text())["candidates"]:
        for st in c["dependencies"].get("sourcetypes", []):
            scen_by_st[st].add(c["candidate_id"])
    industries_by_scn = defaultdict(set)
    for m in json.loads((CATALOG / "explorer_taxonomy.json").read_text())["scenario_industries"]:
        for i in m["industries"]:
            industries_by_scn[m["scenario_id"]].add(i)
    for c in json.loads((CATALOG / "scenario_candidates.json").read_text())["candidates"]:
        for i in c["industries"]:
            industries_by_scn[c["candidate_id"]].add(i["id"])

    def match(st):
        if st in exact:
            return "EXACT", exact[st]
        if st.lower() in ci:
            return "CASE_INSENSITIVE", ci[st.lower()]
        if st in alias:
            return "CATALOG_ALIAS", alias[st]
        return None, None

    def st_state(canon):
        c = cov[canon["splunk_sourcetype"]]
        if c["generator"] == "NATIVE_ENGINE":
            return "PRESENT_NATIVE_VERIFIED" if c["format_verified"] == "YES" else "PRESENT_NATIVE_UNVERIFIED"
        return "PRESENT_SAMPLE_REPLAY" if c["generator"] == "SAMPLE_REPLAY" else "PRESENT_NO_GENERATOR"

    apps, st_rows = [], {}
    for a in snap["apps"]:
        uid = str(a["uid"]) if a["uid"] else None
        p = pinned_by.get(uid) or {}
        api = a.get("api_v1") or {}
        cl = classified.get(uid) or {}
        declared = sorted({s for sts in (p.get("rel_tags_st") or {}).values() for s in sts})
        text = " ".join([a["csv_name"], p.get("appid") or "", p.get("short_desc") or "", api.get("description") or ""])
        roles = roles_for(text)
        bucket = cl.get("bucket")
        # Splunk-built "Add-on for <third-party product>" (NGINX, Office 365, AWS...) parses third-party telemetry: in scope, not platform internals
        platform = bucket == "splunk_platform" and not re.match(r"^Splunk (Supported )?Add-on for ", a["csv_name"])
        canon_vendor = cl.get("canonical_vendor")
        vendor_present = bool(canon_vendor and canon_vendor in vendors)
        vendor_key = canon_vendor or ({"recognized_technology_vendor": cl.get("alias"), "product_only": cl.get("product")}.get(bucket)) or None
        matched = []
        for s in declared:
            kind, canon = match(s)
            if canon:
                matched.append((s, kind, canon))
        if matched:  # a declared sourcetype that is canonical proves the vendor exists, even where the app's publisher is Splunk (e.g. Add-on for NGINX)
            vendor_present = True
            vendor_key = vendor_key or matched[0][2]["vendor_id"]
        row = {"csv_row": a["csv_row"], "csv_name": a["csv_name"], "uid": uid, "url": api.get("url") or (f"https://splunkbase.splunk.com/app/{uid}/" if uid else None),
               "appid": p.get("appid") or api.get("appid"), "publisher": p.get("author"), "publisher_is_partner": p.get("author_is_partner"),
               "categories": p.get("categories"), "downloads_pinned": p.get("downloads"), "latest_version_pinned": p.get("rel_version"), "updated_pinned": p.get("updated"),
               "latest_version_api": (api.get("latest_release") or {}).get("version"), "supported_splunk_versions": (api.get("latest_release") or {}).get("product_versions"),
               "cim_versions": (api.get("latest_release") or {}).get("cim_versions"), "license": api.get("license_name"), "access": p.get("access"),
               "documentation": api.get("documentation"), "support": api.get("support"), "in_pinned_snapshot": bool(p), "api_metadata": bool(api and "error" not in api),
               "vendor_bucket": bucket, "vendor_key": vendor_key, "vendor_in_pulseforge": vendor_present, "roles": roles, "role_basis": "KEYWORD_HEURISTIC_ON_NAME_AND_DESCRIPTION",
               "declared_sourcetypes": declared, "declared_count": len(declared)}
        # app-level classification
        if p.get("is_directory_listing"):
            cls = "OUT_OF_SCOPE"; why = "directory listing app: no telemetry of its own"
        elif not p:
            cls = "INSUFFICIENT_EVIDENCE"; why = "not in the pinned snapshot (newer than 2026-10-26 or absent); no declared sourcetypes available"
        elif platform:
            cls = "OUT_OF_SCOPE"; why = "Splunk-built platform app (not an add-on for a third-party product); declared sourcetypes are platform internals"
        elif not declared:
            cls = "INSUFFICIENT_EVIDENCE"; why = "Splunkbase lists no sourcetypes for this release; none are inferred from the name"
        elif matched:
            states = Counter(st_state(c) for _, _, c in matched)
            cls = ("PRESENT_NATIVE_VERIFIED" if states["PRESENT_NATIVE_VERIFIED"] else "PRESENT_NATIVE_UNVERIFIED" if states["PRESENT_NATIVE_UNVERIFIED"]
                   else "PRESENT_SAMPLE_REPLAY" if states["PRESENT_SAMPLE_REPLAY"] else "PRESENT_NO_GENERATOR")
            why = "%d of %d declared sourcetypes are canonical in PulseForge" % (len(matched), len(declared))
        elif vendor_present:
            cls = "MISSING_SOURCETYPE"; why = "vendor %s exists in PulseForge but none of the declared sourcetypes are canonical" % canon_vendor
        else:
            cls = "MISSING_VENDOR_PRODUCT"; why = "no PulseForge vendor for this product (bucket %s)" % bucket
        row["classification"], row["classification_basis"] = cls, why
        row["api_collector_gap"] = "API_COLLECTOR" in roles and cls in ("MISSING_VENDOR_PRODUCT", "MISSING_SOURCETYPE", "PRESENT_NO_GENERATOR", "PRESENT_SAMPLE_REPLAY")
        row["protocol_collector_gap"] = bool(re.search(UNSUPPORTED_PROTOCOL, text, re.I))
        row["canonical_matches"] = sorted({c["splunk_sourcetype"] for _, _, c in matched})
        apps.append(row)
        for s in declared:
            e = st_rows.setdefault(s, {"sourcetype": s, "declared_by_uids": [], "declared_by_apps": [], "vendor_keys": set(), "classes_of_declaring_apps": set()})
            e["declared_by_uids"].append(uid); e["declared_by_apps"].append(a["csv_name"]); e["vendor_keys"].add(vendor_key or ""); e["classes_of_declaring_apps"].add(cls)
            e.setdefault("_vendor_present", False)
            e["_vendor_present"] = e["_vendor_present"] or vendor_present
            e.setdefault("_platform_only", True)
            e["_platform_only"] = e["_platform_only"] and platform
    # sourcetype-level rows (unique by exact declared spelling)
    out_st = []
    for s, e in sorted(st_rows.items(), key=lambda kv: kv[0].lower()):
        kind, canon = match(s)
        if canon:
            state = st_state(canon)
            c = cov[canon["splunk_sourcetype"]]
            row = {"sourcetype": s, "match_kind": kind, "canonical_sourcetype": canon["splunk_sourcetype"], "pulseforge_support": state, "generator": c["generator"],
                   "byte_verified": c["format_verified"], "independently_indexed": c["indexed_evidence"], "ta_parsing_checked_lab": canon["splunk_sourcetype"] in ta_checked,
                   "classification": state}
            blockers = []
        else:
            if e["_platform_only"]:
                cls = "OUT_OF_SCOPE"
            elif e["_vendor_present"]:
                cls = "MISSING_SOURCETYPE"
            else:
                cls = "MISSING_VENDOR_PRODUCT"
            row = {"sourcetype": s, "match_kind": None, "canonical_sourcetype": None, "pulseforge_support": "ABSENT", "generator": None, "byte_verified": None,
                   "independently_indexed": None, "ta_parsing_checked_lab": False, "classification": cls}
        scn = sorted(scen_by_st.get(row["canonical_sourcetype"] or s, []))
        row.update({"declared_by_uids": sorted(set(e["declared_by_uids"])), "declared_by_app_count": len(set(e["declared_by_uids"])),
                    "vendor_keys": sorted(k for k in e["vendor_keys"] if k), "scenarios_naming_it": scn,
                    "industries": sorted({i for sid in scn for i in industries_by_scn.get(sid, [])})})
        out_st.append(row)
    return apps, out_st, uncovered, vendors, cat, cov, scen_by_st


def attack_data_counts(root):
    """sourcetype -> number of pinned-corpus datasets (splunk/attack_data yml manifests) that label bytes with it; {} when the checkout is absent."""
    counts = Counter()
    if root.is_dir():
        for f in root.glob("datasets/**/*.yml"):
            for st in set(re.findall(r"sourcetype:\s*([^\s#]+)", f.read_text(errors="ignore"))):
                counts[st.strip("\"'")] += 1
    return counts


def write_outputs(args):
    apps, st_rows, uncovered, vendors, cat, cov, scen_by_st = crossref(args)
    ad = attack_data_counts(Path(args.attack_data))
    for r in st_rows:
        r["attack_data_datasets"] = ad.get(r["sourcetype"], 0) if ad else None
        # a MISSING_SOURCETYPE is only a *candidate* until authentic bytes exist; with them it is a quick-win candidate (still subject to review)
        r["gap_evidence"] = ("QUICK_WIN_CANDIDATE" if r["classification"] == "MISSING_SOURCETYPE" and r["attack_data_datasets"] else
                             "CANDIDATE_NO_AUTHENTIC_BYTES" if r["classification"] == "MISSING_SOURCETYPE" else None)
    snap = json.loads(SNAP.read_text())
    cls_apps = Counter(a["classification"] for a in apps)
    cls_st = Counter(r["classification"] for r in st_rows)
    vend_gap = sorted({(a["vendor_key"] or a["csv_name"]) for a in apps if a["classification"] == "MISSING_VENDOR_PRODUCT"})
    doc = {"schema_version": "1.0", "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "inputs": {"addon_csv": snap["source"], "api_v1": snap["api"],
                      "pinned_snapshot": "catalog/vendor_universe/splunkbase_apps_snapshot.json (declared sourcetypes: rel_tags_st; fetched 2026-10-26)"},
           "counts": {"addon_rows": len(apps), "uid_joined": sum(1 for a in apps if a["uid"]), "in_pinned_snapshot": sum(a["in_pinned_snapshot"] for a in apps),
                      "api_v1_metadata": sum(a["api_metadata"] for a in apps), "apps_declaring_sourcetypes": sum(1 for a in apps if a["declared_count"]),
                      "unique_declared_sourcetypes": len(st_rows), "apps_by_classification": dict(cls_apps), "sourcetypes_by_classification": dict(cls_st),
                      "missing_sourcetype_quick_win_candidates": sum(r["gap_evidence"] == "QUICK_WIN_CANDIDATE" for r in st_rows),
                      "missing_sourcetype_without_authentic_bytes": sum(r["gap_evidence"] == "CANDIDATE_NO_AUTHENTIC_BYTES" for r in st_rows),
                      "vendor_product_gaps_apps": cls_apps["MISSING_VENDOR_PRODUCT"], "api_collector_gap_apps": sum(a["api_collector_gap"] for a in apps),
                      "protocol_collector_gap_apps": sum(a["protocol_collector_gap"] for a in apps)},
           "notes": ["Sourcetypes are those Splunkbase DECLARES for a release; none inferred from product names.",
                     "Vendor/product gaps (MISSING_VENDOR_PRODUCT) are NOT counted as sourcetype gaps.",
                     "Role labels are keyword heuristics on name/description, not package inspection (packages need a Splunkbase login)."],
           "apps": apps, "sourcetypes": st_rows}
    (EVID / "crossref.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    cols = ["csv_row", "csv_name", "uid", "url", "publisher", "latest_version_api", "supported_splunk_versions", "cim_versions", "license", "roles", "vendor_bucket", "vendor_key",
            "vendor_in_pulseforge", "declared_count", "canonical_matches", "classification", "classification_basis", "api_collector_gap", "protocol_collector_gap"]
    with open(V / "pulseforge_splunkbase_crossref.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for a in apps:
            w.writerow([";".join(map(str, a[c])) if isinstance(a[c], (list, tuple)) else a[c] for c in cols])
    scols = ["sourcetype", "classification", "match_kind", "canonical_sourcetype", "pulseforge_support", "generator", "byte_verified", "independently_indexed", "ta_parsing_checked_lab",
             "gap_evidence", "attack_data_datasets", "declared_by_app_count", "declared_by_uids", "vendor_keys", "scenarios_naming_it", "industries"]
    with open(V / "pulseforge_splunkbase_crossref_sourcetypes.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(scols)
        for r in st_rows:
            w.writerow([";".join(map(str, r[c])) if isinstance(r[c], list) else r[c] for c in scols])
    print(json.dumps(doc["counts"], indent=1)); print("vendor/product gaps:", len(vend_gap))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--addon", default=str(HOME / "addon.csv"))
    s.add_argument("--uids", default=str(HOME / "splunkbase_addons.csv"))
    s.add_argument("--from-cache")
    c = sub.add_parser("crossref")
    c.add_argument("--attack-data", default=str(HOME / "attack_data"))
    args = ap.parse_args()
    if args.cmd == "snapshot":
        snapshot(args)
    else:
        write_outputs(args)
