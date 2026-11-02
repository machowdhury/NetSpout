#!/usr/bin/env python3
"""Generate the sourcetype and scenario reference documents from the repository's own registries and evidence (nothing is typed by hand).

  docs/reference/SOURCETYPE_REFERENCE.md + sourcetype_coverage.json/.csv
  docs/reference/SCENARIO_REFERENCE.md   + scenario_coverage.json/.csv
Maturity columns are evidence-derived and kept separate (CATALOGED, GENERATOR, FORMAT/BYTE verified, INDEXED, TA parsing checked in a lab, CIM: never validated here).
Run with the project virtualenv:  PYTHONPATH=src:backend python scripts/generate_reference_docs.py
"""
import csv
import glob
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "docs" / "reference"
J = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def sourcetype_reference():
    rows = J("catalog/sourcetypes.json")
    vendors = {v["id"]: v for v in J("catalog/vendors.json")}
    cov = {r["sourcetype"]: r for r in csv.DictReader(open(ROOT / "docs/verification/pulseforge_sourcetype_coverage.csv"))}
    replay = {s["sourcetype"]: s for s in J("catalog/replay_sources.json")["sources"] if s.get("sourcetype")}
    xref = {r["sourcetype"]: r for r in J("docs/verification/evidence/splunkbase/crossref.json")["sourcetypes"]}
    ta_lab = {e["sourcetype_emitted"] for e in J("docs/verification/evidence/ta_validation/windows_sysmon.json")["events"] if e["variant"] == "B" and e["indexed"]}
    from netspout_core import replay_packs
    import build_scenario_dashboards as gen
    scen = defaultdict(set)
    for s in gen.sources():
        for st in s["required_sourcetypes"]:
            scen[st].add(s["id"])
    prov = {}
    for f in sorted(glob.glob(str(ROOT / "catalog/universe_batch[0-9].json"))):
        d = json.load(open(f))
        for src in d.get("sources", []):
            prov.setdefault(src["splunk_sourcetype"], (Path(f).name + ": " + (d.get("provenance") if isinstance(d.get("provenance"), str) else json.dumps(d.get("provenance", ""))[:140])))
    out = []
    for r in rows:
        st = r["splunk_sourcetype"]
        c = cov.get(st, {})
        rp = replay.get(st)
        pv = (f"authentic recording, splunk/attack_data pinned commit {rp['provenance'].get('pinned_commit')}" if rp and rp["provenance"].get("pinned_commit") else
              "vendored recording" if rp else prov.get(st) or ("vendored replay sample " + r["sample_file"] if r.get("sample_file") else "none recorded"))
        x = xref.get(st)
        out.append({"vendor_id": r["vendor_id"], "vendor": (vendors.get(r["vendor_id"]) or {}).get("name", r["vendor_id"]), "product": r["display_name"], "sourcetype": st, "category": r["category"],
                    "data_kind": r["data_kind"], "protocol": r["protocol"], "native_generator": c.get("generator") == "NATIVE_ENGINE", "generator_tier": c.get("generator", "NONE"),
                    "sample_replay_catalog": c.get("generator") == "SAMPLE_REPLAY", "recorded_replay_source": bool(rp), "provenance": pv,
                    "format_byte_verified": c.get("format_verified") == "YES", "independently_indexed": c.get("indexed_evidence") == "YES",
                    "ta_required": r.get("required_ta"), "ta_review": (r.get("required_ta_review") or {}).get("status"), "splunkbase_declared_by": (x or {}).get("declared_by_uids", []),
                    "ta_parsing_checked_in_lab": st in ta_lab, "cim_validated": False, "scenarios": sorted(scen.get(st, [])), "status": r["status"]})
    return out


def md_sourcetypes(rows):
    cnt = Counter()
    for r in rows:
        cnt["native"] += r["native_generator"]
        cnt["byte"] += r["format_byte_verified"]
        cnt["indexed"] += r["independently_indexed"]
        cnt["replay"] += r["recorded_replay_source"]
        cnt["ta"] += r["ta_parsing_checked_in_lab"]
        cnt["scen"] += bool(r["scenarios"])
    L = ["# Sourcetype Coverage Reference", "", f"Generated {today} by `scripts/generate_reference_docs.py` from `catalog/sourcetypes.json`, the coverage evidence and the replay registry. Machine-readable: `sourcetype_coverage.json` / `sourcetype_coverage.csv`.", "",
         "| Measure | Count |", "|---|---|", f"| Cataloged sourcetypes | {len(rows)} |", f"| Native generator | {cnt['native']} |", f"| Byte-verified (HEC raw equality in Splunk) | {cnt['byte']} |",
         f"| Independently indexed | {cnt['indexed']} |", f"| Recorded replay source (authentic recording, continuous replay) | {cnt['replay']} |", f"| TA parsing checked in an isolated lab | {cnt['ta']} |",
         "| CIM validated | 0 (no CIM data model is installed in any lab) |", f"| Referenced by at least one dashboard-backed scenario | {cnt['scen']} |", "",
         "Columns are separate evidence. A sample-replay catalog entry is **not** a native generator; a recorded replay source is **not** coverage of the catalog sourcetype unless its sourcetype name matches. `TA` shows the add-on named by the catalog (`verified` = Splunkbase declares that exact sourcetype for the app; declaration only). `TA lab` means parsing was exercised with the installed package; nothing else was.", "",
         "Legend: **G** native generator, **R** sample-replay catalog only, **-** none; **B** byte-verified; **I** independently indexed; **RR** recorded replay source; **TA lab** parsing checked; **CIM** never validated.", ""]
    byv = defaultdict(list)
    for r in rows:
        byv[r["vendor"]].append(r)
    for v in sorted(byv, key=lambda k: (-len(byv[k]), k)):
        L += [f"## {v} ({len(byv[v])})", "", "| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(byv[v], key=lambda x: x["sourcetype"]):
            g = "G" if r["native_generator"] else ("R" if r["sample_replay_catalog"] else "-")
            ta = (r["ta_required"] or "-") + (" (verified)" if r["ta_review"] == "VERIFIED_DECLARED_BY_SPLUNKBASE" else "")
            L.append(f"| `{r['sourcetype']}` | {r['product']} | {r['data_kind']} | {r['protocol']} | {g} | {'Y' if r['format_byte_verified'] else '-'} | {'Y' if r['independently_indexed'] else '-'} | {'Y' if r['recorded_replay_source'] else '-'} | {ta} | {'Y' if r['ta_parsing_checked_in_lab'] else '-'} | {len(r['scenarios']) or '-'} | {r['provenance'][:70]} |")
        L.append("")
    return "\n".join(L) + "\n"


def scenario_reference():
    from app.main import _explorer
    import build_scenario_dashboards as gen
    ex = _explorer()
    srcs = {s["id"]: s for s in gen.sources(include_blocked=True)}
    tax = {i["id"]: i["name"] for i in J("catalog/explorer_taxonomy.json")["industries"]}
    out, seen = [], set()
    for e in ex.all_entries():
        if e["kind"] != "operational" or e["scenario_id"] in seen:
            continue
        seen.add(e["scenario_id"])
        s = srcs.get(e["scenario_id"], {})
        d = e.get("dashboard") or {}
        out.append({"scenario_id": e["scenario_id"], "title": e["title"], "engine": e["engine"], "execution": ("hybrid" if set(e.get("source_modes") or []) == {"native", "replay"} else "replay" if e.get("source_modes") == ["replay"] else "native" if e["runnable"] else "none"),
                    "category": e.get("category") or e.get("domain"), "kind": s.get("kind"), "industries": [i["id"] for i in e["industries"]], "industry_basis": sorted({i["basis"] for i in e["industries"]}),
                    "subindustry": (e["industries"][0].get("subindustry_label") if e["industries"] else None) or s.get("subindustry"), "summary": e["summary"], "objective": s.get("objective"),
                    "vendors": e.get("vendors", []), "sourcetypes": e.get("sourcetypes") or s.get("required_sourcetypes", []), "phases": [p["id"] for p in s.get("phases", [])] if s else [],
                    "maturity_tier": e["maturity"]["tier"], "runnable": e["runnable"], "blocked_reason": e.get("blocked_reason"), "independently_indexed": e["live_verified"],
                    "dashboard": d.get("splunk_view"), "dashboard_maturity": d.get("dashboard_maturity"), "legacy_dashboard_verified": e["dashboard_verified"],
                    "detection_prerequisites": s.get("detection_prerequisites"), "provenance": s.get("provenance"),
                    "verification_spl": ('index=<index> netspout_scenario_id="%s" %s=<run id> | stats count by netspout_phase, sourcetype' % (s.get("scenario_value", e["scenario_id"]), s.get("key_field", "netspout_run_id"))) if e["runnable"] else None})
    return out, tax


def md_scenarios(rows, tax):
    c = Counter(r["maturity_tier"] for r in rows)
    L = ["# Scenario Coverage Reference", "", f"Generated {today} by `scripts/generate_reference_docs.py` from the Use Case Explorer registry (all scenario registries merged and deduplicated by scenario id). Machine-readable: `scenario_coverage.json` / `scenario_coverage.csv`.", "",
         "| Measure | Count |", "|---|---|", f"| Unique operational scenario definitions | {len(rows)} |", f"| Runnable (a real generator and run path exist) | {sum(r['runnable'] for r in rows)} |",
         f"| Cataloged candidates only (documented, not executable) | {sum(r['maturity_tier'] == 'CATALOGED' for r in rows)} |", f"| Independently indexed in an isolated lab | {sum(r['independently_indexed'] for r in rows)} |",
         f"| With a Dashboard Studio dashboard | {sum(1 for r in rows if r['dashboard'])} |",
         f"| Dashboards DATA_VALIDATED or better | {sum(1 for r in rows if r['dashboard_maturity'] in ('DASHBOARD_DATA_VALIDATED', 'DASHBOARD_VISUALLY_VERIFIED'))} |",
         f"| Dashboards VISUALLY_VERIFIED | {sum(1 for r in rows if r['dashboard_maturity'] == 'DASHBOARD_VISUALLY_VERIFIED')} |", "| Detection verified | 0 (no add-on, CIM or Enterprise Security content installed) |", "",
         "Tiers (as recorded, never upgraded by indexing): " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())) + ".", "",
         "The original 100 financial-services and 100 telecom use-case libraries were not supplied; they are **not** part of these counts and none of the scenarios below were derived from them. Industry mappings are editorial unless an industry pack binds them. Splunk Analytic Stories are a separate reference universe (see the Explorer's Security view); they are not counted as scenarios.", "",
         "## How the counts relate (one partition, plus overlapping attributes)", "",
         "| Group | Count | Meaning |", "|---|---|---|",
         f"| Runnable | {sum(r['runnable'] for r in rows)} | A real generator and run path exist; every one has a Dashboard Studio dashboard |",
         f"| Contract only | {sum((not r['runnable']) and r['maturity_tier'] != 'CATALOGED' for r in rows)} | A topology or format contract exists but no executable telemetry (reason recorded per scenario) |",
         f"| Cataloged only | {sum(r['maturity_tier'] == 'CATALOGED' for r in rows)} | Documented candidates with no execution path |",
         f"| Total | {len(rows)} | The three groups above are mutually exclusive and add up to the total |",
         "", f"**Overlapping attributes** (not additional groups): *independently indexed* ({sum(r['independently_indexed'] for r in rows)}) is a subset of the runnable group, i.e. runnable scenarios whose events from a fresh run were read back from Splunk by an independent search in an isolated lab (scenario-level live checks, dashboard data validation, the monitored runs and the flow scenarios); {sum(r['runnable'] and not r['independently_indexed'] for r in rows)} runnable scenarios lack that proof. Earlier status reports counted 76 because they used only the scenario-level live-equality evidence; the dashboard data validation (a fresh run per scenario, read back from Splunk by run id, KPIs equal to separately written searches) extends the same kind of proof to every runnable scenario, which is why the figure is now higher. The two numbers measure different evidence, not different scenarios. *Tier* (CERTIFIED, VALIDATED, CONTRACTED, ...) is the maturity recorded by the catalog and is never upgraded by indexing.", "",
         "## Coverage by approved industry", "", "| Industry | Definitions | Runnable | Indexed | Dashboards | Dashboards data-validated |", "|---|---|---|---|---|---|"]
    for iid, name in tax.items():
        mine = [r for r in rows if iid in r["industries"]]
        L.append(f"| {name} | {len(mine)} | {sum(r['runnable'] for r in mine)} | {sum(r['independently_indexed'] for r in mine)} | {sum(1 for r in mine if r['dashboard'])} | {sum(1 for r in mine if r['dashboard_maturity'] in ('DASHBOARD_DATA_VALIDATED', 'DASHBOARD_VISUALLY_VERIFIED'))} |")
    L += ["", "## Runnable scenarios", "", "| ID | Title | Execution | Kind | Industries | Sourcetypes | Indexed | Dashboard | Dashboard maturity |", "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted((x for x in rows if x["runnable"]), key=lambda x: x["scenario_id"]):
        L.append(f"| `{r['scenario_id']}` | {r['title'][:70]} | {r['execution']} ({r['engine']}) | {r['kind'] or '-'} | {', '.join(r['industries'][:3]) or 'not mapped'} | {len(r['sourcetypes'])} | {'Y' if r['independently_indexed'] else '-'} | {r['dashboard'] or '-'} | {(r['dashboard_maturity'] or '-').replace('DASHBOARD_', '')} |")
    L += ["", "## Not runnable", "", "| ID | Title | Tier | Reason |", "|---|---|---|---|"]
    for r in sorted((x for x in rows if not x["runnable"]), key=lambda x: (x["maturity_tier"], x["scenario_id"])):
        L.append(f"| `{r['scenario_id']}` | {r['title'][:70]} | {r['maturity_tier']} | {(r['blocked_reason'] or '')[:110]} |")
    return "\n".join(L) + "\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    st = sourcetype_reference()
    (OUT / "SOURCETYPE_REFERENCE.md").write_text(md_sourcetypes(st), encoding="utf-8")
    (OUT / "sourcetype_coverage.json").write_text(json.dumps({"generated": today, "rows": st}, indent=1) + "\n", encoding="utf-8")
    with open(OUT / "sourcetype_coverage.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(st[0]))
        for r in st:
            w.writerow([";".join(map(str, v)) if isinstance(v, list) else v for v in r.values()])
    sc, tax = scenario_reference()
    (OUT / "SCENARIO_REFERENCE.md").write_text(md_scenarios(sc, tax), encoding="utf-8")
    (OUT / "scenario_coverage.json").write_text(json.dumps({"generated": today, "rows": sc}, indent=1) + "\n", encoding="utf-8")
    with open(OUT / "scenario_coverage.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(sc[0]))
        for r in sc:
            w.writerow([";".join(map(str, v)) if isinstance(v, list) else v for v in r.values()])
    print(json.dumps({"sourcetypes": len(st), "scenarios": len(sc), "runnable": sum(r["runnable"] for r in sc), "dashboards": sum(1 for r in sc if r["dashboard"])}))


if __name__ == "__main__":
    main()
