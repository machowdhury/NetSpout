#!/usr/bin/env python3
"""Audit of the installed Dashboard Studio views from their actual JSON: visualization mix, layout and panel-query signatures, so repetition and weak designs are measured, not guessed.
Usage: python scripts/audit_dashboards.py     Evidence: docs/verification/evidence/dashboards/design_audit.json"""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = []
for f in sorted((ROOT / "netspout/default/data/ui/views").glob("pf_*.xml")):
    m = re.search(r"<definition><!\[CDATA\[(.*?)\]\]></definition>", f.read_text(encoding="utf-8"), re.S)
    if not m:
        continue
    d = json.loads(m.group(1))
    viz = d.get("visualizations", {})
    types = [v.get("type", "?").split(".")[-1] for v in viz.values()]
    layout = d.get("layout", {})
    tabs = [t.get("label") for t in (layout.get("tabs", {}).get("items", []) if isinstance(layout.get("tabs"), dict) else [])]
    drill = sum(1 for v in viz.values() if v.get("eventHandlers"))
    queries = [ds.get("options", {}).get("query", "") for ds in d.get("dataSources", {}).values()]
    rows.append({"view": f.stem, "panels": len(viz), "viz_mix": dict(collections.Counter(types)), "tabs": tabs, "drilldowns": drill, "datasources": len(queries),
                 "uses_mstats": any("mstats" in q for q in queries), "signature": "|".join(sorted(collections.Counter(types).elements())),
                 "layout_type": layout.get("type"), "n_inputs": len(d.get("inputs", {}))})
sig = collections.Counter(r["signature"] for r in rows)
fam = collections.Counter((r["layout_type"], tuple(r["tabs"])) for r in rows)
vizkinds = collections.Counter(k for r in rows for k in r["viz_mix"])
out = {"dashboards": len(rows), "distinct_viz_signatures": len(sig), "largest_signature_groups": [{"signature": s, "count": n} for s, n in sig.most_common(5)],
       "distinct_layout_tab_families": len(fam), "viz_type_totals": dict(vizkinds), "no_drilldown": [r["view"] for r in rows if not r["drilldowns"]],
       "single_viz_kind": [r["view"] for r in rows if len(r["viz_mix"]) <= 2], "few_panels": [r["view"] for r in rows if r["panels"] < 5], "rows": rows}
(ROOT / "docs/verification/evidence/dashboards/design_audit.json").write_text(json.dumps(out, indent=1) + "\n")
print({k: out[k] for k in ("dashboards", "distinct_viz_signatures", "distinct_layout_tab_families", "viz_type_totals")})
print("top signature groups:", [(g["count"], g["signature"][:90]) for g in out["largest_signature_groups"]])
print("no drilldown:", len(out["no_drilldown"]), " <=2 viz kinds:", len(out["single_viz_kind"]), " <5 panels:", len(out["few_panels"]))
