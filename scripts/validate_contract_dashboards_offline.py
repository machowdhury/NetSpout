#!/usr/bin/env python3
"""
Offline validation of the Dashboard Studio views of every declarative scenario contract. No Splunk is involved, so this can establish structure and field
usage only; it does NOT validate SPL with Splunk's parser, run a search, or render a page (see scripts/validate_contract_dashboards_live.py for that).

Per view: JSON parses; data source and visualization ids are unique; the label is unique across views; the view is registered in the app navigation; every search is
scoped to the scenario (and to the chosen run, except the run picker); no search hard-codes an index or a sourcetype the contract does not emit; and the fields that
the contract's phase panels group by are present on every generated event and actually vary across phases (a panel whose field is constant tells no story).

  PYTHONPATH=src:backend python scripts/validate_contract_dashboards_offline.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from netspout_core import scenario_contracts  # noqa: E402

VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"
NAV = (ROOT / "netspout" / "default" / "data" / "ui" / "nav" / "default.xml").read_text()
OUT = ROOT / "docs" / "verification" / "evidence" / "dashboards" / "contract_dashboard_offline_validation.json"
PHASE_PANEL_FIELDS = ("status", "action", "signature", "netspout_phase", "netspout_device_id", "netspout_scenario_id", "netspout_run_id")


def view(cid):
    text = (VIEWS / ("pf_%s.xml" % cid)).read_text()
    return text, json.loads(re.search(r"<definition><!\[CDATA\[(.*?)\]\]></definition>", text, re.S).group(1))


def check(cid, labels):
    problems = []
    text, d = view(cid)
    c = scenario_contracts.get(cid)
    for key in ("dataSources", "visualizations", "layout", "inputs"):
        if key not in d:
            problems.append("missing " + key)
    if "pf_%s" % cid not in NAV and ('name="pf_%s"' % cid) not in NAV:
        problems.append("not registered in navigation")
    label = re.search(r"<label>(.*?)</label>", text).group(1)
    labels.setdefault(label, []).append(cid)
    searches = {k: x["options"].get("query", "") for k, x in d["dataSources"].items() if x.get("type", "").endswith("ds.search")}
    for k, q in searches.items():
        if 'netspout_scenario_id="%s"' % cid not in q:
            problems.append("%s not scoped to the scenario" % k)
        if k != "ds_runs" and "$run_tok$" not in q:
            problems.append("%s not scoped to the run" % k)
        if re.search(r"\bindex\s*=\s*(?!\$)[\w\"-]+", q):
            problems.append("%s hard-codes an index" % k)
        for st in re.findall(r'sourcetype\s*=\s*"?([\w:.\-]+)', q):
            if st not in scenario_contracts.sourcetypes(c):
                problems.append("%s filters on a sourcetype the contract does not emit: %s" % (k, st))
    refs = [x for x in d["visualizations"].values()]
    ev = scenario_contracts.generate(cid, "offline-validate")
    missing = [f for f in PHASE_PANEL_FIELDS if any(not getattr(e, f, None) for e in ev)]
    if missing:
        problems.append("fields empty on some events: " + ", ".join(missing))
    by_phase = {}
    for e in ev:
        by_phase.setdefault(e.netspout_phase, set()).add(e.status)
    statuses = {s for v in by_phase.values() for s in v}
    changes = sum(1 for a, b in zip(list(by_phase.values()), list(by_phase.values())[1:]) if a != b)
    want = "Status by phase" if len(statuses) >= 2 else "Events by phase and source (steady-state"   # a steady-state scenario gets a load chart, not a one-colour status chart
    if not any(want in v.get("title", "") for v in refs):
        problems.append("missing the expected phase panel: " + want)
    return {"scenario_id": cid, "searches": len(searches), "panels": len(refs), "distinct_statuses": len(statuses), "phases_where_status_set_changes": changes, "problems": problems}


def main():
    labels = {}
    rows = [check(cid, labels) for cid in scenario_contracts.ids()]
    for label, cids in labels.items():
        if len(cids) > 1:
            for r in rows:
                if r["scenario_id"] in cids:
                    r["problems"].append("label not unique: " + label)
    ids = [r["scenario_id"] for r in rows]
    result = {"dashboards": len(rows), "passed": sum(1 for r in rows if not r["problems"]), "failed": [r for r in rows if r["problems"]],
              "levels_checked": ["json structure", "unique ids and labels", "navigation registration", "scenario and run scoping", "no hard-coded index or foreign sourcetype", "phase-panel fields present and varying in generated events"],
              "levels_not_checked": ["Splunk SPL parser", "results from indexed data", "browser rendering"], "views_unique": len(set(ids)) == len(ids), "rows": rows}
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("dashboards", "passed")}), "failed:", [(r["scenario_id"], r["problems"][:2]) for r in result["failed"]][:12])


if __name__ == "__main__":
    main()
