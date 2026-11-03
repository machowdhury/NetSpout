#!/usr/bin/env python3
"""Derive docs/contracts/ta_live_results.json from the live evidence files written by scripts/ta_compat.py.
A sourcetype is recorded as passed only if its evidence has zero FAIL and no live check NOT_RUN. Nothing is hand-edited."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVID = {  # sourcetype -> (spec, evidence written after the fix)
    "cisco:asa": ("tests/ta_specs/cisco_asa.json", "docs/verification/evidence/ta_compat/cisco_asa_ta_compat_phase4_revalidation.json"),
    "fortigate_traffic": ("tests/ta_specs/fortinet_fortigate.json", "docs/verification/evidence/ta_compat/fortigate_traffic_after_fix.json"),
    "pan:traffic": ("tests/ta_specs/palo_alto_traffic.json", "docs/verification/evidence/ta_compat/pan_traffic_after_fix.json"),
    "cisco:ios": ("tests/ta_specs/cisco_ios_catalyst.json", "docs/verification/evidence/ta_compat/cisco_ios_after_fix.json"),
}


def main():
    out = {}
    for st, (spec, ev) in EVID.items():
        d = json.loads((ROOT / ev).read_text())
        live_rows = [r for r in d["checks"] if r["check"].startswith(("hec.", "index.", "field[", "ownership.", "timestamp.parsed", "eventtype[", "tags[", "absent[", "search.", "lab.", "routing."))]
        passed = d["summary"]["FAIL"] == 0 and live_rows and all(r["status"] == "PASS" for r in live_rows)
        out[st] = {"passed": bool(passed), "package": d["ta"]["package"], "version": d["ta"]["version"], "spec": spec, "evidence": ev, "run_id": d.get("run_id"), "summary": d["summary"],
                   "not_run": [r["check"] for r in d["checks"] if r["status"] == "NOT_RUN"], "generated": d["generated"]}
    (ROOT / "docs/contracts/ta_live_results.json").write_text(json.dumps(out, indent=1) + "\n")
    for k, v in out.items():
        print(k, v["passed"], v["summary"])


if __name__ == "__main__":
    main()
