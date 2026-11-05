#!/usr/bin/env python3
"""Machine-readable inventory of sample files. Every YAML is classified by the structured replay parser (src/netspout_core/yaml_sample_replay.py):
REPLAYABLE | UNRESOLVED_PLACEHOLDER | UNSUPPORTED | INVALID | OVERSIZE. Nothing is guessed; configuration text is never counted as an event.

  python scripts/inventory_samples.py [CORPUS_DIR ...]      default: netspout/appserver/static/samples (shipped) and ./samples (external corpus, if present)
Writes docs/verification/evidence/sample_replay/sample_inventory.json
"""
import collections
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from netspout_core.catalog import NetSpoutCatalog  # noqa: E402
from netspout_core.telemetry_dispatcher import is_metric_sourcetype  # noqa: E402
from netspout_core.yaml_sample_replay import validate_sample_file  # noqa: E402

OUT = ROOT / "docs" / "verification" / "evidence" / "sample_replay" / "sample_inventory.json"


def main(dirs):
    cat = NetSpoutCatalog()
    by_st = {s["splunk_sourcetype"]: s for s in cat._sourcetypes}
    rows, other = [], collections.Counter()
    for label, d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "*", "*.y*ml"))):
            r = validate_sample_file(f)
            sts = r["sourcetypes"]
            meta = [by_st[s] for s in sts if s in by_st]
            kinds = sorted({m.get("data_kind", "event") for m in meta} | ({"metric"} if any(is_metric_sourcetype(s) for s in sts) else set()))
            rows.append({"corpus": label, "file": os.path.relpath(f, ROOT) if str(ROOT) in f else f, "dir": os.path.basename(os.path.dirname(f)),
                         "status": r["status"], "events": r["events"], "adapters": r["adapters"], "claimed_sourcetypes": sts,
                         "catalog_sourcetypes": [m["splunk_sourcetype"] for m in meta], "vendors": sorted({m["vendor_id"] for m in meta}),
                         "kinds": kinds or ["unknown"], "unresolved_placeholders": r["unresolved"], "error": r["error"], "bytes": os.path.getsize(f)})
        for f in glob.glob(os.path.join(d, "*", "*")):
            if not f.endswith((".yml", ".yaml")):
                other[(label, os.path.splitext(f)[1] or "(none)")] += 1
    summary = {label: dict(collections.Counter(r["status"] for r in rows if r["corpus"] == label)) for label, _ in dirs}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "non_yaml_files": {"%s%s" % k: v for k, v in sorted(other.items())}, "rows": rows}, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    args = sys.argv[1:]
    dirs = [("shipped", str(ROOT / "netspout/appserver/static/samples")), ("corpus", str(ROOT / "samples"))] if not args else [(os.path.basename(a), a) for a in args]
    main([(l, d) for l, d in dirs if os.path.isdir(d)])
