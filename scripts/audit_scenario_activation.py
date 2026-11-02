#!/usr/bin/env python3
"""
Classify every non-runnable scenario definition and account for dashboards, from the coverage data and the shipped views. Nothing is hand-set:
a scenario is never marked runnable here; this only records why each one is not and what it would take.

  A  directly activatable: a runnable scenario already covers every needed sourcetype with the same purpose
  B  activatable by configuration or mapping onto existing runnable content
  C  needs new scenario logic: its sourcetypes have generators, but there is no executable layer (phases, shared hosts and identities)
  D  blocked: a needed data source is not in the catalog, has no generator, or the definition names none, so the schema cannot be verified

  PYTHONPATH=src:backend python scripts/audit_scenario_activation.py
Writes docs/reference/scenario_activation_audit.json and SCENARIO_ACTIVATION_AUDIT.md.
"""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "docs" / "reference"
VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"
GEN = ("NATIVE_ENGINE", "SAMPLE_REPLAY")


def structural_spl_ok(q):
    """Delimiters balanced, non-empty, and a recognizable start. This is NOT a Splunk parse; it only catches broken text."""
    q = (q or "").strip()
    if not q or not re.match(r"^(\||search\b|index\s*=|\||\|\s*(tstats|mstats|inputlookup|makeresults|rest)|\$|`|\()", q, re.I):
        return False
    body = re.sub(r'"(?:\\.|[^"\\])*"', '""', q)
    return body.count('"') % 2 == 0 and all(body.count(a) == body.count(b) for a, b in ("()", "[]"))


def dashboards(srows):
    n, spl_ok, bad = 0, 0, []
    for f in sorted(VIEWS.glob("pf_*.xml")):
        m = re.search(r"<definition><!\[CDATA\[(.*?)\]\]></definition>", f.read_text(encoding="utf-8"), re.S)
        if not m:
            continue
        n += 1
        d = json.loads(m.group(1))
        qs = [ds.get("options", {}).get("query", "") for ds in d.get("dataSources", {}).values() if ds.get("type", "").endswith("ds.search")]
        if qs and all(structural_spl_ok(q) for q in qs):
            spl_ok += 1
        else:
            bad.append(f.stem)
    mat = collections.Counter(r.get("dashboard_maturity") for r in srows if r.get("dashboard"))
    return {"dashboard_views": n, "structural_spl_ok": spl_ok, "structural_spl_failed": bad,
            "data_validated_or_better": mat["DASHBOARD_DATA_VALIDATED"] + mat["DASHBOARD_VISUALLY_VERIFIED"], "visually_verified": mat["DASHBOARD_VISUALLY_VERIFIED"], "implemented_not_data_validated": mat["DASHBOARD_IMPLEMENTED"]}


def classify(r, T, runnable):
    need = r["sourcetypes"]
    if r["engine"] == "scenario_runner":
        missing = [s for s in need if s not in T]
        nogen = [s for s in need if s in T and T[s]["generator_tier"] not in GEN]
        covers = [q["scenario_id"] for q in runnable if need and set(need) <= set(q["sourcetypes"])]
        if missing or nogen:
            why = "no generator for " + ", ".join(nogen + missing)
            return "D", why + " (not in the catalog)" if missing and not nogen else why
        extra = " The same sourcetypes are emitted by runnable `%s`, which is a different scenario, so aliasing would only relabel it." % covers[0] if covers else ""
        return "C", "Every sourcetype has a generator, but this definition has no executable layer: it needs per-phase telemetry with shared hosts and identities, and generators run separately do not share entities." + extra
    hints = [x for x in T if x and re.search(r"(?<![a-z0-9_:.\-])" + re.escape(x.lower()) + r"(?![a-z0-9_\-])", r.get("_hint", ""))]
    if not hints:
        return "D", "The definition names no sourcetype in the catalog, so the data source and its schema cannot be verified without inventing them."
    gen = [h for h in hints if T[h]["generator_tier"] in GEN]
    if not gen:
        return "D", "Names " + ", ".join(hints) + ", which has no generator."
    return "C", "Names %s (generator exists), but only as free text: no scenario sequence, entities or phases are defined, and a single-sourcetype run is already available from the catalog." % ", ".join(gen)


def event_families(T):
    """The generator's own event families per sourcetype (only those it enumerates); used for the customer telemetry table."""
    from app.generator_modes import generator_service as g
    out = {}
    for st in T:
        try:
            r = g._universe_source(st)
        except Exception:
            continue
        if r and isinstance(r[0], dict) and r[0].get("event_families"):
            out[st] = list(r[0]["event_families"])
    return out


def main():
    srows = json.loads((REF / "scenario_coverage.json").read_text())["rows"]
    T = {x["sourcetype"]: x for x in json.loads((REF / "sourcetype_coverage.json").read_text())["rows"]}
    cand = {c["candidate_id"]: c for c in json.loads((ROOT / "catalog" / "scenario_candidates.json").read_text())["candidates"]}
    runnable = [r for r in srows if r["runnable"]]
    (REF / "sourcetype_event_families.json").write_text(json.dumps(event_families(T), indent=1, sort_keys=True))
    out = []
    for r in srows:
        if r["runnable"]:
            continue
        c = cand.get(r["scenario_id"])
        r = dict(r, _hint=json.dumps({k: v for k, v in (c or {}).items() if k != "url"}).lower())
        cls, why = classify(r, T, runnable)
        out.append({"scenario_id": r["scenario_id"], "title": r["title"], "engine": r["engine"], "class": cls, "reason": why, "sourcetypes": r["sourcetypes"],
                    "summary": r.get("summary"), "source": (c or {}).get("source_id")})
    counts = collections.Counter(o["class"] for o in out)
    try:
        from netspout_core import scenario_contracts
        contract_rows = scenario_contracts.catalog()
    except Exception:
        contract_rows = []
    activation = {"by_fidelity": dict(collections.Counter(c["fidelity"] for c in contract_rows)), "by_generator_family": dict(collections.Counter(c["generator_family"] for c in contract_rows)),
                  "previously_runnable": len(runnable) - len(contract_rows) if not out else len(runnable)}
    data = {"defined": len(srows), "runnable": len(runnable), "non_runnable": len(out), "classes": dict(counts), "newly_activated": len(contract_rows), "activation": activation, "dashboards": dashboards(srows), "rows": out}
    (REF / "scenario_activation_audit.json").write_text(json.dumps(data, indent=1) + "\n")
    d = data["dashboards"]
    L = ["# Scenario activation audit", "",
         "Generated by `scripts/audit_scenario_activation.py` from the coverage data and the scenario contracts; do not edit by hand. It never changes a status: it records why a scenario is not runnable, or how it became runnable.", "",
         "| | Count |", "|---|---|", "| Defined scenarios | %d |" % data["defined"], "| Runnable | %d |" % data["runnable"], "| Not runnable | %d |" % data["non_runnable"],
         "| Runnable before declarative contracts | %d |" % activation["previously_runnable"], "| Activated by declarative contracts | %d |" % len(contract_rows), ""]
    if contract_rows:
        L += ["## How the activated scenarios run", "",
              "Each is a declarative contract (`catalog/scenario_contracts.json`): shared topology, ordered phases, and streams that bind an existing generator to a node. Fidelity is derived from the streams, never declared.", "",
              "| Fidelity | Meaning | Scenarios |", "|---|---|---|",
              "| VENDOR_NATIVE | Only vendor formatters from the engine | %d |" % activation["by_fidelity"].get("VENDOR_NATIVE", 0),
              "| MIXED | Native formatters or verbatim samples plus a labeled modeled stand-in for a sourcetype with no generator | %d |" % activation["by_fidelity"].get("MIXED", 0),
              "| MODELED | Only the labeled NetSpout schema `netspout:scenario:state` (a state progression or monitoring use case, not a vendor log format) | %d |" % activation["by_fidelity"].get("MODELED", 0), "",
              "| Generator family | Scenarios |", "|---|---|"] + ["| %s | %d |" % (k, v) for k, v in sorted(activation["by_generator_family"].items())] + [""]
    if out:
        L += ["| Class | Meaning | Count |", "|---|---|---|",
              "| A | Directly activatable with existing generators | %d |" % counts["A"], "| B | Activatable by configuration or mapping | %d |" % counts["B"],
              "| C | Needs new scenario logic (generators exist, scenario layer does not) | %d |" % counts["C"],
              "| D | Blocked: data source unknown, not cataloged, or without a generator | %d |" % counts["D"], ""]
    d = data["dashboards"]
    L += [         "## Dashboards", "", "| | Count |", "|---|---|", "| Dashboard views shipped | %d |" % d["dashboard_views"],
         "| Structural SPL check passed (delimiters balanced; **not** a Splunk parse) | %d |" % d["structural_spl_ok"],
         "| Data-validated or better (registry maturity) | %d |" % d["data_validated_or_better"], "| Visually verified (registry maturity) | %d |" % d["visually_verified"],
         "| Implemented, **not** validated against data or rendered (JSON and structural SPL checks only) | %d |" % d["implemented_not_data_validated"], "",
         "Not verified for any dashboard in this audit: Splunk's SPL parser, results against indexed data, browser rendering.", ""]
    if out:
        L += ["## Scenarios", "", "| ID | Name | Class | Why it is not runnable |", "|---|---|---|---|"]
    for o in out:
        L.append("| `%s` | %s | %s | %s |" % (o["scenario_id"], o["title"][:80].replace("|", "/"), o["class"], o["reason"].replace("|", "/")))
    (REF / "SCENARIO_ACTIVATION_AUDIT.md").write_text("\n".join(L) + "\n")
    print(json.dumps({k: data[k] for k in ("defined", "runnable", "non_runnable", "classes", "dashboards")}, indent=1)[:900])


if __name__ == "__main__":
    main()
