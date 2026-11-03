#!/usr/bin/env python3
"""catalog/capability_status.json: the slim, UI-facing capability record per catalog sourcetype and per scenario.

Derived ONLY from evidence files (never from catalog tier labels):
  docs/contracts/phase5/master_matrix.json   generator really produced events, offline format check, naming/payload/routing conflicts
  docs/contracts/ta_live_results.json        live Splunk verification (Phase 4); only entries with passed=true count
  docs/reference/scenario_coverage.json      scenario -> required sourcetypes and runnable flag

Statuses: VERIFIED | FORMAT_CHECKED | GENERATOR_UNVERIFIED | UNSUPPORTED. A block (generation disabled) exists only for: no generator, metric/event routing conflict, add-on payload conflict.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = {"VERIFIED": "Verified in Splunk", "FORMAT_CHECKED": "Format checked, not live verified", "GENERATOR_UNVERIFIED": "Generator available, unverified", "UNSUPPORTED": "Unsupported or incompatible"}
ROUTING_MSG = ("NetSpout would send this as a metric-index payload, but the matching add-on (%s) defines it as an event sourcetype. Sending it as a metric would break the add-on's searches and turning it into a log "
               "would change what the data means, so generation is disabled until a verified implementation exists.")


def record(r, live):
    st = r["catalog_sourcetype"]
    rec = {"vendor_id": r["catalog_vendor"], "vendor": r["catalog_vendor_name"], "product": r["catalog_product"], "sourcetype": st, "kind": r["catalog_data_kind"],
           "ta": {"app": r["ta_app_id"], "version": r["package_version"], "canonical_sourcetype": r["canonical_ta_sourcetype"], "match": r["match_type"]} if r["ta_app_id"] else None,
           "generator": r["generator_mode"] if r["generator_valid"] else None, "notes": [], "block": None}
    routing = [c for c in r["conflicts"] if c.startswith("routing")]
    payload = [c for c in r["conflicts"] if c.startswith("payload")]
    naming = [c for c in r["conflicts"] if c.startswith("naming")]
    lv = live.get(st)
    if routing:
        rec["status"] = "UNSUPPORTED"
        rec["block"] = {"code": "ROUTING_CONFLICT", "message": ROUTING_MSG % r["ta_app_id"]}
    elif not r["generator_valid"]:
        rec["status"] = "UNSUPPORTED"
        rec["block"] = {"code": "NO_GENERATOR", "message": "NetSpout has no verified generator or sample for this sourcetype, so it cannot produce realistic events for it (%s)." % (r["generator_error"] or "no events produced")}
    elif payload:
        rec["status"] = "UNSUPPORTED"
        rec["block"] = {"code": "PAYLOAD_CONFLICT", "message": "NetSpout's events for this sourcetype do not match the extraction rules of its add-on (%s), so Splunk would index them unparsed." % r["ta_app_id"]}
    elif r["live_verification"].startswith("SPLUNK_VERIFIED") and lv and lv.get("passed"):
        rec["status"] = "VERIFIED"
        rec["evidence"] = {"add_on": "%s %s" % (r["ta_app_id"], r["package_version"]), "live_checks": lv["summary"], "file": lv["evidence"]}
    elif r["format_verification"] == "FORMAT_VERIFIED":
        rec["status"] = "FORMAT_CHECKED"
    else:
        rec["status"] = "GENERATOR_UNVERIFIED"
    if rec["status"] == "FORMAT_CHECKED":
        rec["notes"].append("NetSpout's events satisfy the add-on's own extraction rules in an offline check; not yet tested in Splunk.")
    if rec["status"] == "GENERATOR_UNVERIFIED":
        if r["match_type"] == "none":
            rec["notes"].append("No downloaded add-on covers this vendor; the event format is NetSpout's own and its parsing in Splunk is untested.")
        elif r["match_type"] == "candidate":
            rec["notes"].append("An add-on exists for this vendor but none of its sourcetypes corresponds to this name; parsing is untested.")
        else:
            rec["notes"].append("The format has not been checked against the add-on in Splunk.")
    if naming:
        rec["notes"].append(naming[0].replace("naming: ", "Name differs from the add-on: "))
    if r["format_verification"] in ("FORMAT_PARTIAL", "STRUCTURE_ONLY"):
        rec["notes"].append("Only part of the add-on's field extraction could be compared offline.")
    rec["status_label"] = LABEL[rec["status"]]
    return rec


def main():
    m = json.loads((ROOT / "docs/contracts/phase5/master_matrix.json").read_text())["rows"]
    live = json.loads((ROOT / "docs/contracts/ta_live_results.json").read_text())
    sts = {r["catalog_sourcetype"]: record(r, live) for r in m}
    scen = []
    for s in json.loads((ROOT / "docs/reference/scenario_coverage.json").read_text())["rows"]:
        scen.append({"id": s["scenario_id"], "title": s["title"], "category": s.get("category"), "summary": s.get("summary"), "sourcetypes": s["sourcetypes"], "engine": s.get("engine"),
                     "catalog_runnable": bool(s["runnable"]), "catalog_blocked_reason": s.get("blocked_reason"), "dashboard": s.get("dashboard"), "dashboard_maturity": s.get("dashboard_maturity")})
    out = {"generated_from": ["docs/contracts/phase5/master_matrix.json", "docs/contracts/ta_live_results.json", "docs/reference/scenario_coverage.json"], "labels": LABEL, "sourcetypes": sts, "scenarios": scen}
    (ROOT / "catalog/capability_status.json").write_text(json.dumps(out, separators=(",", ":")) + "\n")
    from collections import Counter
    print(Counter(r["status"] for r in sts.values()), Counter((r["block"] or {}).get("code") for r in sts.values()), len(scen))


if __name__ == "__main__":
    main()
