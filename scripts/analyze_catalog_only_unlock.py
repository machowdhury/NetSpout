#!/usr/bin/env python3
"""Which catalog-only scenarios could be unlocked by the sourcetypes PulseForge can already stream, and what each still lacks.
Reads the registries only; it changes no status. Usage: PYTHONPATH=src:backend python scripts/analyze_catalog_only_unlock.py
Evidence: docs/verification/evidence/coverage/catalog_only_unlock.json"""
import collections
import json
from pathlib import Path

import app.main as m
from app.catalog import catalog
from app.generator_modes import generator_service as g

ROOT = Path(__file__).resolve().parents[1]
st = {s["splunk_sourcetype"]: s for s in catalog.list_sourcetypes(include_deprecated=True)}


def mode(name):
    s = st.get(name)
    if not s:
        return "not_in_catalog"
    try:
        return g.prepare_sourcetype_entries(s["vendor_id"], name, 1)[1]["mode"]
    except ValueError:
        return "not_streamable"


ex = m._explorer()
items = ex.search(q="", limit=200)["items"]
for off in range(200, ex.search(q="", limit=1)["total"], 200):
    items += ex.search(q="", limit=200, offset=off)["items"]
blocked = [e for e in items if e["kind"] == "operational" and not e.get("runnable")]
cands = [e for e in blocked if e.get("engine") == "cataloged"]
contracts = {s["id"]: s for s in catalog.list_scenarios()}
rows = []
for e in blocked:
    if e.get("engine") == "cataloged":
        continue
    sc = contracts.get(e["scenario_id"], {})
    modes = {n: mode(n) for n in sc.get("sourcetypes", [])}
    rows.append({"scenario_id": e["scenario_id"], "maturity": e["maturity"]["raw"], "sourcetypes": modes, "all_sourcetypes_streamable": all(v in ("native", "grounded_sample") for v in modes.values()),
                 "expected_phases": sc.get("expected_phases"), "affected_entities": sc.get("affected_entities"),
                 "missing_for_authentic_run": "per-phase telemetry mapping and correlated entities (the catalog gives generic phase names and one affected entity)"})
out = {"catalog_only_total": len(blocked), "documented_candidates": len(cands), "candidates_with_any_sourcetype_binding": sum(1 for e in cands if e.get("sourcetypes") or e.get("source_ids")),
       "contract_only": len(rows), "contract_only_with_all_sourcetypes_streamable": sum(r["all_sourcetypes_streamable"] for r in rows),
       "candidate_industries": dict(collections.Counter((e["industries"][0]["id"] if e["industries"] else "unmapped") for e in cands).most_common(8)), "contract_rows": rows,
       "conclusion": "No scenario was converted. Candidates are titles with no sourcetype binding or phases; contracts have generic phases and no per-phase telemetry mapping. Tagging recorded samples with phase names would invent a correlation."}
(ROOT / "docs/verification/evidence/coverage/catalog_only_unlock.json").write_text(json.dumps(out, indent=1) + "\n")
print({k: v for k, v in out.items() if k not in ("contract_rows", "candidate_industries")})
