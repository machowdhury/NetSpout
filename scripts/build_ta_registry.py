#!/usr/bin/env python3
"""TA-backed compatibility registry.

Reads the downloaded add-on packages (in memory, from ~/netspout/private-packs; they are never copied into the repository), the NetSpout catalog
(docs/reference/sourcetype_coverage.json), the sample inventory and the generators, and writes:

  docs/contracts/ta_backed_registry.json      one row per add-on-defined sourcetype, plus the reverse view of NetSpout catalog entries
  docs/contracts/ta_mismatch_report.json      prioritized conflicts with evidence

Statuses (a row carries a list; each is earned separately):
  TA_DEFINED          the sourcetype is defined in the package configuration (file:stanza recorded)
  GENERATOR_AVAILABLE NetSpout can produce events for that exact sourcetype name (native formatter or a valid sample)
  FORMAT_VERIFIED     NetSpout's rendered events were checked against the add-on's own definitions (see format_check for the method and numbers)
  SPLUNK_VERIFIED     set only from live evidence files (docs/verification/evidence/ta_compat/*.json), never by this script's own checks
  UNSUPPORTED         no valid implementation for the exact name
  CONFLICT            NetSpout's name, payload or routing conflicts with the add-on (conflict_types lists why)
Matching is exact by name; a near match (same vendor, similar name) is recorded as a candidate and is always a CONFLICT (different name), never a support claim.
"""
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from ta_compat import _rx  # noqa: E402
from ta_inventory import app_roots, read_package  # noqa: E402

PACKS = Path("~/netspout/private-packs").expanduser()
EVID = ROOT / "docs/verification/evidence"
# vendor ids in the NetSpout catalog that belong to each add-on (used only for near-name candidates)
PKG_VENDORS = {
    "aristanetworks": ["arista_eos"], "TA_cisco_catalyst": ["cisco_catalyst", "cisco_ios", "cisco_sdwan", "cisco_ise"], "Splunk_TA_Cisco_Intersight": ["cisco_intersight"],
    "Splunk_TA_cisco_meraki": ["cisco_meraki"], "TA-cisco-cloud-security-addon": ["cisco_umbrella", "cisco_secure_access"], "CiscoSecurityCloud": ["cisco_duo", "cisco_asa", "cisco_secure_endpoint", "cisco_firepower"],
    "ta_cisco_thousandeyes": ["cisco_thousandeyes", "thousandeyes"], "Splunk_TA_fortinet_fortigate": ["fortinet"], "Splunk_TA_cisco-asa": ["cisco_asa"], "Splunk_TA_cisco-esa": ["cisco_esa"],
    "Splunk_TA_cisco-wsa": ["cisco_wsa"], "Splunk_TA_juniper": ["juniper_junos"], "Splunk_TA_paloalto_networks": ["palo_alto"]}


def payload_format(raw):
    s = raw.lstrip()
    if s.startswith("{") or s.startswith("["):
        try:
            json.loads(s)
            return "json"
        except ValueError:
            return "json-like (invalid)"
    if s.startswith("<") and re.match(r"^<\d+>", s):
        return "syslog-rfc3164/5424 with PRI"
    if s.startswith("<"):
        return "xml"
    if s.startswith("CEF:"):
        return "cef"
    if re.match(r"^[A-Z][a-z]{2} +\d+ \d\d:\d\d:\d\d", s):
        return "bsd-syslog text"
    if re.match(r"^\d{4}[-/]\d\d[-/]\d\d", s) or re.match(r"^\d{4}/\d\d/\d\d", s):
        return "timestamp-prefixed text"
    if len(re.findall(r"\b[\w.-]+=(?:\"[^\"]*\"|\S+)", s)) >= 3:
        return "key=value"
    if s.count(",") >= 8:
        return "csv-like"
    return "plain text"


def load_ta_defs(pkgs):
    """sourcetype -> definitions with regexes/delimiters (kept in memory only; none of this text is written to the repository)."""
    defs = {}
    from ta_compat import parse_conf
    for pkg in pkgs:
        files, _ = read_package(str(pkg))
        for root in app_roots(files):
            g = lambda rel: files.get("%s/%s" % (root, rel), "")
            props, trans = parse_conf(g("default/props.conf")), parse_conf(g("default/transforms.conf"))
            force_all = [(n, t) for n, t in trans.items() if t.get("DEST_KEY") == "MetaData:Sourcetype" and t.get("REGEX") and str(t.get("FORMAT", "")).startswith("sourcetype::")]
            for st, kv in props.items():
                if st == "default" or re.match(r"^(source|host|rule|delayedrule)::", st):
                    continue
                regs, delims = [], []
                for k, v in kv.items():
                    if k.startswith("REPORT-"):
                        for n in (x.strip() for x in v.split(",")):
                            t = trans.get(n)
                            if not t:
                                continue
                            if t.get("REGEX") and not t.get("DEST_KEY"):
                                regs.append(("REPORT:" + n, t["REGEX"]))
                            elif t.get("DELIMS"):
                                delims.append((n, t["DELIMS"], [f.strip() for f in t.get("FIELDS", "").split(",") if f.strip()]))
                    elif k.startswith("EXTRACT-"):
                        regs.append(("EXTRACT:" + k[8:], re.sub(r"\s+in\s+\w+\s*$", "", v)))
                force = []
                for n, t in force_all:
                    fmt = t["FORMAT"][len("sourcetype::"):]
                    pat = re.escape(fmt).replace(r"\$1", "(.+)").replace("$1", "(.+)")
                    if re.fullmatch(pat, st):
                        force.append((n, t["REGEX"]))
                defs.setdefault(st, []).append({"app": root.rsplit("/", 1)[-1], "regexes": regs, "delims": delims, "force": force, "kv_mode": kv.get("KV_MODE"), "rename": kv.get("rename"), "time_format": kv.get("TIME_FORMAT")})
    return defs


def format_check(raws, defn):
    """Test rendered events against the add-on's own definitions. Heuristic: Python's re stands in for Splunk's PCRE; compile failures are counted, never hidden."""
    out = {"events": len(raws), "method": None}
    if not raws:
        return dict(out, method="no events")
    kv = defn["kv_mode"]
    if kv == "json" and not defn["regexes"] and not defn["delims"]:
        ok = 0
        for r in raws:
            try:
                ok += isinstance(json.loads(r), dict)
            except ValueError:
                pass
        return dict(out, method="json parse (add-on KV_MODE=json, no regex extractions; checks structure only, not field names)", json_objects=ok, passes=(ok == len(raws)))
    compiled, bad = [], 0
    for name, rx in defn["regexes"]:
        try:
            compiled.append((name, _rx(rx)))
        except re.error:
            bad += 1
    ok, partial = [], []
    for r in raws:
        hit = any(c.search(r) for _, c in compiled)
        part = False
        if not hit:
            for _, d, f in defn["delims"]:
                if not f:                                   # DELIMS without FIELDS = key=value pairs: the event must contain several
                    hit = hit or len(re.findall(r"[A-Za-z_][\w.\-]*=", r)) >= 3
                else:
                    cols = len(r.split(d.strip('"') if d.count('"') == 2 and d.startswith('"') else d))
                    hit = hit or cols >= len(f)
                    part = part or (cols >= 10 and cols < len(f))   # right format, fewer columns than the add-on lists: Splunk fills the first ones
        ok.append(hit)
        partial.append(part)
    fm = None
    if defn["force"]:
        try:
            frx = [_rx(x) for _, x in defn["force"]]
            fm = sum(1 for r in raws if any(f.search(r) for f in frx))
        except re.error:
            fm = None
    out.update(method="add-on extractions (REPORT/EXTRACT regexes, DELIMS/FIELDS) and sourcetype-routing regex applied to rendered events", regexes=len(defn["regexes"]), delim_transforms=len(defn["delims"]),
               regex_compile_errors=bad, events_with_any_extraction=sum(ok), partial_column_events=sum(partial), force_sourcetype_match=fm)
    out["passes"] = bool(compiled or defn["delims"]) and all(ok) and (fm is None or fm == len(raws))
    return out


def main():
    inv = json.loads((EVID / "ta_inventory/packages.json").read_text())
    pkgs = [PACKS / p["package"] for p in inv["packages"]]
    defs = load_ta_defs(pkgs)
    cov = json.loads((ROOT / "docs/reference/sourcetype_coverage.json").read_text())["rows"]
    cat = {r["sourcetype"]: r for r in cov}
    samp = json.loads((EVID / "sample_replay/sample_inventory.json").read_text())["rows"]
    claims = {}
    for r in samp:
        for st in r["claimed_sourcetypes"]:
            claims.setdefault(st, []).append({"corpus": r["corpus"], "file": r["file"], "status": r["status"]})
    from netspout_core.generator_modes import TelemetryGeneratorService, _NATIVE
    svc = TelemetryGeneratorService()
    live = {}
    lr = ROOT / "docs/contracts/ta_live_results.json"        # derived from the live evidence files by scripts/record_ta_live_results.py
    if lr.exists():
        for st, rec in json.loads(lr.read_text()).items():
            live[st] = rec if rec.get("passed") else None

    ta_names = {}
    rows = []
    for pkg in inv["packages"]:
        for app in pkg["apps"]:
            for s in app["sourcetypes"]:
                ta_names.setdefault(s["sourcetype"], []).append(app["id"])
    cache = {}

    def render(st):
        if st in cache:
            return cache[st]
        c = cat.get(st)
        try:
            ents, prov = svc.prepare_sourcetype_entries(c["vendor_id"], st, 6)
            cache[st] = ([e.raw_log for e in ents], prov, None)
        except Exception as exc:
            cache[st] = ([], None, str(exc)[:160])
        return cache[st]

    for pkg in inv["packages"]:
        for app in pkg["apps"]:
            vendors = PKG_VENDORS.get(app["id"], [])
            for s in app["sourcetypes"]:
                st = s["sourcetype"]
                wh = s["declared_by"][0]
                inp = [i for i in app["inputs"] if i["sourcetype"] == st]
                row = {"package": pkg["package"], "package_id": app["id"], "package_version": app["version"], "package_label": app["label"], "canonical_sourcetype": st,
                       "defined_in": [d["where"] for d in s["declared_by"]], "input_type": ("modular input / API: " + ", ".join(sorted({i["stanza"].split("://")[0] for i in inp}))) if inp else "not declared by the package (operator chooses syslog, file, HEC or collector)",
                       "ta_behavior": {k: v for k, v in {"time_format": (s["props"] or {}).get("TIME_FORMAT"), "kv_mode": (s["props"] or {}).get("KV_MODE"), "report_transforms": len((s["props"] or {}).get("report_transforms", [])),
                                                         "extract": (s["props"] or {}).get("extract_count"), "eval": (s["props"] or {}).get("eval_count"), "eventtypes": s["eventtypes"]}.items() if v not in (None, 0, [])},
                       "vendor": None, "product": app["label"], "netspout": None, "statuses": ["TA_DEFINED"], "conflict_types": [], "format_check": None, "evidence": [wh["where"] + " in " + pkg["package"]], "limitations": []}
                c = cat.get(st)
                if c:
                    raws, prov, err = render(st)
                    mode = "native" if st in _NATIVE else (prov or {}).get("mode")
                    row["vendor"] = c["vendor_id"]
                    row["netspout"] = {"catalog_sourcetype": st, "match": "EXACT", "catalog_vendor": c["vendor_id"], "catalog_product": c["product"], "generator_tier": c["generator_tier"], "data_kind": c["data_kind"],
                                       "generator_mode": mode, "sample_source": (prov or {}).get("source") or c["provenance"], "payload_format": payload_format(raws[0]) if raws else None, "routing": "metric index" if c["data_kind"] == "metric" else "event index",
                                       "generation_error": err}
                    if raws:
                        row["statuses"].append("GENERATOR_AVAILABLE")
                        dlist = [d for d in defs.get(st, []) if d["app"] == app["id"]] or defs.get(st, [])
                        if dlist:
                            fc = format_check(raws, dlist[0])
                            row["format_check"] = fc
                            if fc.get("passes"):
                                row["statuses"].append("FORMAT_VERIFIED")
                            elif fc.get("events_with_any_extraction") == 0 and fc.get("partial_column_events"):
                                row["limitations"].append("NetSpout emits fewer columns than the add-on's positional extraction lists (right format, partial coverage); Splunk fills only the leading fields")
                            elif fc.get("events_with_any_extraction") == 0 and (dlist[0]["regexes"] or dlist[0]["delims"]):
                                row["conflict_types"].append("payload-format: none of the add-on's extractions match NetSpout's rendered events")
                            elif fc.get("force_sourcetype_match") == 0:
                                row["conflict_types"].append("payload-format: NetSpout's events do not match the add-on's sourcetype-routing regex")
                    else:
                        row["statuses"].append("UNSUPPORTED")
                        row["limitations"].append("NetSpout cannot generate this sourcetype: " + (err or "no sample"))
                    if c["data_kind"] == "metric" and ((s["props"] or {}).get("KV_MODE") == "json" or s["eventtypes"]) and not (s["props"] or {}).get("metric_schema"):
                        row["conflict_types"].append("routing: NetSpout sends this as a metric-index payload; the add-on defines it as an event sourcetype (no metric schema)")
                    if c["generator_tier"] == "NONE":
                        row["conflict_types"].append("advertised-without-generator: catalog lists the sourcetype but no generator or sample exists")
                    if st not in ("cisco:asa",) and raws:
                        row["limitations"].append("NetSpout HEC metadata fields (action, src_ip, dest_ip, signature, protocol) still shadow add-on fields for this sourcetype; not in TA_PARSED_SOURCETYPES")
                else:
                    row["_near"] = True
                if st in claims:
                    row["sample_claims"] = claims[st][:6]
                    if "UNSUPPORTED" in row["statuses"]:
                        row["statuses"].remove("UNSUPPORTED")
                        row["limitations"].append("a sample file claims this sourcetype but the catalog has no entry with that name")
                lv = live.get(st)
                if lv and lv["package"] == pkg["package"]:           # verification belongs to the package it was run against, not to every package that defines the same name
                    row["statuses"].append("SPLUNK_VERIFIED")
                    row["evidence"].append(lv["evidence"])
                    spec = json.loads((ROOT / lv["spec"]).read_text())
                    row["splunk_verification"] = {"spec": lv["spec"], "package_version": lv["version"], "summary": lv["summary"], "not_run": lv["not_run"], "verified_events": [e["id"] for e in spec["events"]],
                                                  "scope": "only the representative events in the spec; other message types of this sourcetype are not verified"}
                    if "FORMAT_VERIFIED" not in row["statuses"]:
                        row["limitations"].append("SPLUNK_VERIFIED for the fields of the events in the spec; the offline full-format check is not satisfied (NetSpout emits fewer columns than the add-on lists)")
                    row["limitations"] = [x for x in row["limitations"] if not x.startswith("NetSpout HEC metadata fields")]
                if row["conflict_types"]:
                    row["statuses"].append("CONFLICT")
                rows.append(row)
    # near-name candidates: one-to-one, best ratio first, only among the add-on's vendors, never for legacy names the add-on itself renames
    legacy = {st for ds in defs.values() for d in ds for st in [d["rename"]] if st} | {k for k, ds in defs.items() if any(d["rename"] for d in ds)}
    pairs = []
    for r in rows:
        if r.pop("_near", False) and r["canonical_sourcetype"] not in legacy:
            for n, cr in cat.items():
                if cr["vendor_id"] in PKG_VENDORS.get(r["package_id"], []) and n not in ta_names:
                    ratio = difflib.SequenceMatcher(None, r["canonical_sourcetype"].replace("_", ":"), n).ratio()
                    if ratio >= 0.8:
                        pairs.append((ratio, id(r), n))
    used_rows, used_names, byid = set(), set(), {id(r): r for r in rows}
    for ratio, rid, n in sorted(pairs, reverse=True):
        if rid in used_rows or n in used_names:
            continue
        used_rows.add(rid); used_names.add(n)
        r = byid[rid]
        r["netspout"] = {"catalog_sourcetype": n, "match": "NEAR (name similarity %.2f, same vendor; product equivalence NOT confirmed)" % ratio, "generator_tier": cat[n]["generator_tier"]}
        r["vendor"] = cat[n]["vendor_id"]
        r["conflict_types"].append("naming: NetSpout uses %r, the add-on defines %r (candidate only)" % (n, r["canonical_sourcetype"]))
        r["statuses"].append("CONFLICT")
    for r in rows:
        if r["netspout"] is None and "UNSUPPORTED" not in r["statuses"]:
            r["statuses"].append("UNSUPPORTED")
            r["limitations"].append("no NetSpout catalog sourcetype with this name or a confident near-name variant" + ("; legacy intake name that the add-on renames" if r["canonical_sourcetype"] in legacy else ""))
    # reverse view: every catalog entry
    rev = []
    for r in cov:
        st = r["sourcetype"]
        entry = {"catalog_sourcetype": st, "vendor": r["vendor_id"], "generator_tier": r["generator_tier"], "data_kind": r["data_kind"], "ta_required": r.get("ta_required"), "splunkbase_declared_by": r.get("splunkbase_declared_by"),
                 "defined_by_downloaded_packages": ta_names.get(st, []), "category": None, "notes": []}
        if st in ta_names:
            entry["category"] = "TA_DEFINED_EXACT"
        elif r.get("ta_required") or r.get("splunkbase_declared_by"):
            entry["category"] = "CLAIMS_TA_BUT_NOT_DEFINED_IN_DOWNLOADED_PACKAGES"
            entry["notes"].append("the catalog names an add-on (%s) but none of the 14 downloaded packages defines this sourcetype; the package may not be among the 14" % r.get("ta_required"))
        else:
            entry["category"] = "NO_TA_CLAIM"
        rev.append(entry)
    summary = {"ta_sourcetypes": len(rows), "by_status": {s: sum(1 for r in rows if s in r["statuses"]) for s in ("TA_DEFINED", "GENERATOR_AVAILABLE", "FORMAT_VERIFIED", "SPLUNK_VERIFIED", "UNSUPPORTED", "CONFLICT")},
               "exact_matches": sum(1 for r in rows if r["netspout"] and r["netspout"]["match"] == "EXACT"), "near_matches": sum(1 for r in rows if r["netspout"] and r["netspout"]["match"].startswith("NEAR")),
               "catalog": {k: sum(1 for e in rev if e["category"] == k) for k in ("TA_DEFINED_EXACT", "CLAIMS_TA_BUT_NOT_DEFINED_IN_DOWNLOADED_PACKAGES", "NO_TA_CLAIM")}}
    (ROOT / "docs/contracts").mkdir(exist_ok=True)
    (ROOT / "docs/contracts/ta_backed_registry.json").write_text(json.dumps({"summary": summary, "rows": rows, "catalog_reverse_view": rev}, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
