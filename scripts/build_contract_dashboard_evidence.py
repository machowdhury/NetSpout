#!/usr/bin/env python3
"""
Record what has actually been verified about the dashboards of declarative-contract scenarios, derived from the evidence files, never asserted.

Levels (scale as in dashboard_maturity.json): SPECIFIED < IMPLEMENTED < DATA_VALIDATED < VISUALLY_VERIFIED. Each dashboard gets separate flags:
  structural        view exists, Dashboard Studio JSON parses, searches scoped to the scenario, delimiters balanced          (this script computes it)
  parser            every search accepted by Splunk's own SPL parser                                                          (evidence: contract_dashboard_parser_validation.json)
  results           every search executed in Splunk over the scenario's indexed run and returned rows, none failed           (evidence: contract_dashboard_results_validation.json)
  rendered          opened in a browser against the lab Splunk Web, no error text                                             (evidence: contract_dashboard_render*.json)
  inspected         a person or the model opened the screenshot and recorded what it shows                                    (evidence: contract_visual_inspection.json)
Maturity: DATA_VALIDATED needs parser AND results; VISUALLY_VERIFIED needs DATA_VALIDATED AND an inspection entry whose screenshot file exists.

  PYTHONPATH=src:backend python scripts/build_contract_dashboard_evidence.py
"""
import glob
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from audit_scenario_activation import structural_spl_ok  # noqa: E402
from netspout_core import scenario_contracts  # noqa: E402

VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"
EV = ROOT / "docs" / "verification" / "evidence" / "dashboards"
OUT = EV / "contract_dashboard_maturity.json"


def load(name, default):
    f = EV / name
    return json.loads(f.read_text()) if f.exists() else default


def structural(cid):
    f = VIEWS / ("pf_%s.xml" % cid)
    if not f.exists():
        return False
    d = json.loads(re.search(r"<definition><!\[CDATA\[(.*?)\]\]></definition>", f.read_text(encoding="utf-8"), re.S).group(1))
    qs = [x["options"].get("query", "") for x in d["dataSources"].values() if x.get("type", "").endswith("ds.search")]
    return bool(qs) and all(structural_spl_ok(q) and 'netspout_scenario_id="%s"' % cid in q for q in qs)


def main():
    parser = {r["scenario_id"]: not r["parser_errors"] for r in load("contract_dashboard_parser_validation.json", {"rows": []})["rows"]}
    results = {r["scenario_id"]: (r["searches"] > 0 and r["searches_with_rows"] == r["searches"] and not r["searches_failed"]) for r in load("contract_dashboard_results_validation.json", {"rows": []})["rows"]}
    rendered, rendered_ok = set(), set()
    for f in glob.glob(str(EV / "contract_dashboard_render*.json")):
        for r in json.loads(Path(f).read_text())["rows"]:
            rendered.add(r["scenario_id"])
            if r["no_results_text"] == 0 and r["error_text"] == 0:
                rendered_ok.add(r["scenario_id"])
    inspected = {r["scenario_id"]: r for r in load("contract_visual_inspection.json", {"inspected": []})["inspected"]}
    rows = {}
    for cid in scenario_contracts.ids():
        st = structural(cid)
        pv, rv = bool(parser.get(cid)), bool(results.get(cid))
        shot_ok = cid in inspected and (EV / "screens_contract" / inspected[cid]["screenshot"]).exists()
        level = "DASHBOARD_SPECIFIED" if not (VIEWS / ("pf_%s.xml" % cid)).exists() else "DASHBOARD_IMPLEMENTED" if st else "DASHBOARD_SPECIFIED"
        if st and pv and rv:
            level = "DASHBOARD_DATA_VALIDATED"
            if shot_ok and cid in rendered_ok:
                level = "DASHBOARD_VISUALLY_VERIFIED"
        rows[cid] = {"maturity": level, "specified": True, "implemented": st, "structural_spl_ok": st, "splunk_spl_parser_validated": pv, "search_results_validated": rv,
                     "installed_and_opened_in_splunk_web": cid in rendered, "browser_render_checks_pass": cid in rendered_ok, "screenshot_inspected": shot_ok, "data_validated": rv,
                     "family": "contract"}
    OUT.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "scale": "DASHBOARD_SPECIFIED < DASHBOARD_IMPLEMENTED < DASHBOARD_DATA_VALIDATED < DASHBOARD_VISUALLY_VERIFIED",
                               "note": "Derived from the evidence files named in the module docstring; no level is asserted.", "dashboards": rows}, indent=1) + "\n")
    c = {}
    for r in rows.values():
        c[r["maturity"]] = c.get(r["maturity"], 0) + 1
    print(json.dumps({"dashboards": len(rows), **c, "parser_validated": sum(r["splunk_spl_parser_validated"] for r in rows.values()), "results_validated": sum(r["search_results_validated"] for r in rows.values()),
                      "rendered": sum(r["installed_and_opened_in_splunk_web"] for r in rows.values()), "inspected": sum(r["screenshot_inspected"] for r in rows.values())}))


if __name__ == "__main__":
    main()
