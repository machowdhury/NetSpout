#!/usr/bin/env python3
"""
Record what has actually been verified about the dashboards of declarative-contract scenarios, from the shipped views themselves.

Levels (scale as in dashboard_maturity.json): SPECIFIED < IMPLEMENTED < DATA_VALIDATED < VISUALLY_VERIFIED.
This script can only establish IMPLEMENTED: the view file exists, its Dashboard Studio JSON parses, every search is scoped to the scenario, and each
search passes the structural SPL check (balanced delimiters, recognizable start). It does NOT run Splunk's SPL parser, query indexed data or render a page,
so it never records DATA_VALIDATED or VISUALLY_VERIFIED. Those need a Splunk instance and are added only by scripts that run one.

  PYTHONPATH=src:backend python scripts/build_contract_dashboard_evidence.py
"""
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
OUT = ROOT / "docs" / "verification" / "evidence" / "dashboards" / "contract_dashboard_maturity.json"


def check(cid):
    f = VIEWS / ("pf_%s.xml" % cid)
    if not f.exists():
        return {"maturity": "DASHBOARD_SPECIFIED", "specified": True, "implemented": False, "reason": "no view file"}
    d = json.loads(re.search(r"<definition><!\[CDATA\[(.*?)\]\]></definition>", f.read_text(encoding="utf-8"), re.S).group(1))
    qs = [x["options"].get("query", "") for x in d["dataSources"].values() if x.get("type", "").endswith("ds.search")]
    ok = bool(qs) and all(structural_spl_ok(q) and 'netspout_scenario_id="%s"' % cid in q for q in qs)
    return {"maturity": "DASHBOARD_IMPLEMENTED" if ok else "DASHBOARD_SPECIFIED", "specified": True, "implemented": ok, "json_valid": True, "structural_spl_ok": ok,
            "splunk_spl_parser_validated": False, "installed_and_opened_in_splunk_web": False, "data_validated": False, "browser_render_checks_pass": False, "screenshot_inspected": False,
            "searches": len(qs), "family": "contract"}


def main():
    rows = {cid: check(cid) for cid in scenario_contracts.ids()}
    OUT.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "scale": "DASHBOARD_SPECIFIED < DASHBOARD_IMPLEMENTED < DASHBOARD_DATA_VALIDATED < DASHBOARD_VISUALLY_VERIFIED",
                               "note": "Offline evidence only: JSON and structural SPL checks. No Splunk instance was used.", "dashboards": rows}, indent=1) + "\n")
    print(json.dumps({"dashboards": len(rows), "implemented": sum(r["implemented"] for r in rows.values())}))


if __name__ == "__main__":
    main()
