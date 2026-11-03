#!/usr/bin/env python3
"""
Merge reruns into the main live-validation evidence. A scenario is rerun after a fix to its contract or to the generator layer; the rerun row replaces the earlier row for that
scenario in live_validation_all.json (and its run id in live_run_map_all.json), and the replacement is recorded under "reruns" so the history stays visible.

  python scripts/merge_live_validation.py
"""
import glob
import json
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "docs" / "verification" / "evidence" / "scenario_contracts"


def main():
    base = json.loads((D / "live_validation_all.json").read_text())
    rmap = json.loads((D / "live_run_map_all.json").read_text())
    rows = {r["scenario_id"]: r for r in base["rows"]}
    reruns = base.get("reruns", [])
    for f in sorted(glob.glob(str(D / "live_validation_rerun*.json"))):
        name = Path(f).stem
        extra = json.loads(Path(f).read_text())
        rm = json.loads((D / name.replace("live_validation", "live_run_map") ).with_suffix(".json").read_text())
        for r in extra["rows"]:
            reruns.append({"scenario_id": r["scenario_id"], "from": name, "replaced_run_id": rows[r["scenario_id"]]["run_id"], "new_run_id": r["run_id"], "status": r["status"]})
            rows[r["scenario_id"]] = r
            rmap[r["scenario_id"]] = rm[r["scenario_id"]]
    base["rows"] = [rows[k] for k in sorted(rows)]
    base["sampled"], base["passed"], base["reruns"] = len(rows), sum(1 for r in rows.values() if r["status"] == "PASS"), reruns
    (D / "live_validation_all.json").write_text(json.dumps(base, indent=1) + "\n")
    (D / "live_run_map_all.json").write_text(json.dumps(rmap, indent=1) + "\n")
    for f in glob.glob(str(D / "live_validation_rerun*.json")) + glob.glob(str(D / "live_run_map_rerun*.json")):
        Path(f).unlink()   # merged; the replacement history lives in "reruns"
    print(json.dumps({"scenarios": len(rows), "passed": base["passed"], "reruns_recorded": len(reruns)}))


if __name__ == "__main__":
    main()
