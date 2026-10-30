#!/usr/bin/env python3
"""Regenerate docs/verification/pulseforge_{sourcetype,scenario}_coverage.{md,csv} from repository evidence.

Replaces the Phase 3 scanner output (every row UNKNOWN). Nothing is guessed: a tier is only reported when an artifact
in the repo proves it. Tiers, strongest first, per catalog sourcetype:

  generator   NATIVE_ENGINE  a vendor-native formatter in a SplunkLogEngine map or core formatter emits it
              SAMPLE_REPLAY  only a vendored sample file backs it (replay of recorded events)
              NONE           catalogued, nothing generates it
  format      raw-equality PASS: bytes submitted over HEC equal bytes Splunk indexed (catalog/*raw_equality_results.json)
  ta          vendor parser actually installed and exercised (universe_batch4_parser_assessments.json); mapping-only is NOT counted
  indexed     appears in a live raw-equality PASS or in a sourcetype listed by the run-evidence files under docs/verification

Usage: python scripts/generate_coverage_report.py [--check]   (--check prints the summary and writes nothing)
"""
import csv
import glob
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "docs" / "verification"


def load(name):
    return json.loads((ROOT / "catalog" / name).read_text(encoding="utf-8"))


# Modules whose only job is generating one product's telemetry: any quoted catalog sourcetype in them is a generator.
DEDICATED_GENERATORS = ("panos_generator.py", "snmp_splunk_e2e.py")
# Hand-authored per-vendor fault templates: a generator exists but no format reference backs it, so they are reported
# separately and are NOT counted as vendor-native.
FAULT_TEMPLATES = "fault_injection_engine.py"


def _literals(text, catalog_ids, assignment_only=True):
    found = set()
    for s in catalog_ids:
        q = re.escape(s)
        if assignment_only:
            pats = [r"sourcetype\s*=\s*[\"']" + q + r"[\"']", r"sourcetype\s*:\s*str\s*=\s*[\"']" + q + r"[\"']",
                    r"[\"'](?:sourcetype|splunk_sourcetype)[\"']\s*:\s*[\"']" + q + r"[\"']"]
        else:
            pats = [r"[\"']" + q + r"[\"']"]
        if any(re.search(p, text) for p in pats):
            found.add(s)
    return found


def engine_sourcetypes(catalog_ids):
    from netspout_core.log_engine import SplunkLogEngine as E
    mapped = set()
    for attr in dir(E):
        if attr.endswith("SOURCE_SOURCETYPES"):
            mapped |= set(getattr(E, attr))
    literal = set()
    base = ROOT / "src" / "netspout_core"
    for f in ("log_engine.py", "snmp_engine.py", "gnmi_engine.py"):
        literal |= _literals((base / f).read_text(encoding="utf-8"), catalog_ids)
    for f in DEDICATED_GENERATORS:
        literal |= _literals((base / f).read_text(encoding="utf-8"), catalog_ids, assignment_only=False)
    return (mapped | literal) & catalog_ids


def fault_template_only(catalog_ids, native):
    text = (ROOT / "src" / "netspout_core" / FAULT_TEMPLATES).read_text(encoding="utf-8")
    return _literals(text, catalog_ids) - native


def raw_equality_passes():
    passed, live = set(), set()
    for f in glob.glob(str(ROOT / "catalog" / "**" / "*raw_equality_results.json"), recursive=True):
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        for row in data.get("raw_equality", []):
            if row.get("verdict") == "PASS" and row.get("sourcetype"):
                passed.add(row["sourcetype"])
                if "live" in Path(f).name:
                    live.add(row["sourcetype"])
    return passed, live


def evidence_indexed(catalog_ids):
    """Sourcetypes named in committed live-run evidence files (JSON results only, not prose)."""
    found = set()
    for f in glob.glob(str(OUT / "*.json")) + glob.glob(str(OUT / "evidence" / "**" / "*.json"), recursive=True):
        if "reconciliation" in f or "demo_platform" in f:  # catalog dump / unverified platform demo: not live-ingest evidence
            continue
        text = Path(f).read_text(encoding="utf-8")
        found |= {s for s in catalog_ids if f'"{s}"' in text}
    return found


def scenario_evidence():
    """Runnable / live-verified / dashboard / detection evidence for catalog scenarios, from committed artifacts only."""
    from netspout_core.authentic_scenario_packs import SCENARIO_PACK_IDS
    from netspout_core.scenario_runner import SUPPORTED_SCENARIO_IDS
    live = {}
    for f in glob.glob(str(ROOT / "catalog" / "*live_raw_equality_results.json")):
        for run in json.loads(Path(f).read_text(encoding="utf-8")).get("scenario_runs", []):
            if run.get("verdict") == "PASS":
                live[run["scenario_id"]] = Path(f).name
    dash = ROOT / "docs" / "verification" / "evidence" / "phase4f" / "visual-validation.json"
    dashboard_ready = []
    if dash.exists() and json.loads(dash.read_text(encoding="utf-8")).get("verdict", {}).get("maturity") == "DASHBOARD_READY":
        dashboard_ready = ["SEC-P9-B-DNS-ANOMALY (unified generation; Dashboard Studio view pulseforge_dns_anomaly_studio)"]
    sec = ROOT / "docs" / "verification" / "evidence" / "phase4f" / "security-run.json"
    detection = []
    if sec.exists() and json.loads(sec.read_text(encoding="utf-8")).get("scheduler", {}).get("result_count", 0) >= 1:
        detection = ["React2Shell / d36459b1-7901-401a-a67e-44426c15b168 (saved search fired on Splunk's scheduler)"]
    return set(SCENARIO_PACK_IDS), set(SUPPORTED_SCENARIO_IDS), live, dashboard_ready, detection


def main(check=False):
    rows = load("sourcetypes.json")
    ids = {r["splunk_sourcetype"] for r in rows}
    native = engine_sourcetypes(ids)
    fmt, live_fmt = raw_equality_passes()
    indexed = live_fmt | evidence_indexed(ids)
    assess = {a["sourcetype"]: a for a in load("universe_batch4_parser_assessments.json")["sources"]}
    out = []
    for r in rows:
        st = r["splunk_sourcetype"]
        gen = "NATIVE_ENGINE" if st in native else "SAMPLE_REPLAY" if r.get("sample_file") else "NONE"
        a = assess.get(st, {})
        ta = a.get("status", "")
        out.append({
            "vendor_id": r["vendor_id"], "sourcetype": st, "category": r["category"], "data_kind": r["data_kind"],
            "protocol": r["protocol"], "status": r["status"], "generator": gen,
            "format_verified": "YES" if st in fmt else "NO",
            "ta_validated": "PARTIAL" if ta.startswith("ACTUAL_EXECUTION") else "NO",
            "indexed_evidence": "YES" if st in indexed else "NO",
        })
    c = Counter(o["generator"] for o in out)
    n = len(out)
    summary = {
        "catalog_sourcetypes": n, "native_generators": c["NATIVE_ENGINE"], "sample_replay_only": c["SAMPLE_REPLAY"], "no_generator": c["NONE"],
        "format_verified": sum(o["format_verified"] == "YES" for o in out),
        "ta_validated_or_partial": sum(o["ta_validated"] != "NO" for o in out),
        "independently_indexed": sum(o["indexed_evidence"] == "YES" for o in out),
    }
    scenarios = load("scenarios.json")
    mat = Counter(s.get("maturity") for s in scenarios)
    gp = load("golden_path_evidence.json").get("golden_paths", [])
    det = load("phase13a_validation_evidence.json").get("validations", [])
    det_ok = [v for v in det if v.get("status") == "POSITIVE_CASE_VALIDATED"]
    sc_summary = {"catalog_scenarios": len(scenarios), "by_maturity": dict(mat), "golden_path_records": len(gp), "detection_verified": len(det_ok)}
    if check:
        print(json.dumps({"sourcetypes": summary, "scenarios": sc_summary}, indent=1))
        return
    today = date.today().isoformat()
    with open(OUT / "pulseforge_sourcetype_coverage.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(sorted(out, key=lambda o: (o["generator"], o["vendor_id"], o["sourcetype"])))
    by_vendor = Counter(o["vendor_id"] for o in out)
    nat_vendor = Counter(o["vendor_id"] for o in out if o["generator"] == "NATIVE_ENGINE")
    lines = [
        "# PulseForge Sourcetype Coverage", "",
        f"Generated {today} by `scripts/generate_coverage_report.py` from repository evidence (replaces the Phase 3 scanner output).", "",
        "| Measure | Count | Of catalog |", "|---|---|---|",
    ]
    for label, key in (("Cataloged sourcetypes", "catalog_sourcetypes"), ("Vendor-native generator", "native_generators"),
                       ("Sample replay only", "sample_replay_only"), ("No generator", "no_generator"),
                       ("Format verified (byte-equal raw in Splunk)", "format_verified"),
                       ("Vendor TA validated (full or partial)", "ta_validated_or_partial"),
                       ("Independently indexed (live evidence)", "independently_indexed")):
        lines.append(f"| {label} | {summary[key]} | {100 * summary[key] / n:.1f}% |")
    lines += ["", "Tier definitions are in the script header. `TA validated` counts only a parser that was installed and exercised; "
              "mapping-only assessments are not counted. `Sample replay only` is recorded-event replay, not a vendor-native formatter.", "",
              "## Vendors with the most uncovered sourcetypes", "", "| Vendor | Cataloged | Native generator |", "|---|---|---|"]
    gaps = sorted(by_vendor, key=lambda v: -(by_vendor[v] - nat_vendor[v]))[:15]
    for v in gaps:
        lines.append(f"| {v} | {by_vendor[v]} | {nat_vendor[v]} |")
    fault = sorted(fault_template_only(ids, native))
    b5 = {x["splunk_sourcetype"] for x in load("universe_batch5.json")["sources"]} if (ROOT / "catalog" / "universe_batch5.json").exists() else set()
    lines += ["", "## Reconciliation notes", "",
              "* Batch 5 registers 31 sourcetypes but added 30 to the count: `cisco:sdwan:BGP-5-ADJCHANGE` already had a native formatter "
              "(`format_cisco_sdwan_bgp_log`), so it now has two generators. Not a counting defect.",
              "* Scanner fix (Batch 6 pass): sourcetypes declared as default arguments (`sourcetype: str = \"...\"`) and in dedicated generator modules "
              f"({', '.join(DEDICATED_GENERATORS)}) were missed, which hid `pan:system`, `cisco:duo:remote:vpn`, `cisco:catalyst:clienthealth`, "
              "`meraki:assurancealerts`, `netspout:snmp:poll` and `netspout:snmp:trap` (+6).",
              f"* Hand-authored fault-injection templates exist for {len(fault)} more sourcetypes ({', '.join(fault)}) but no format reference backs them, so they are not counted as vendor-native.",
              "* The 70% target (244 of 348) is not reachable on current evidence: the remaining sample-replay rows are demo-authored or empty-poller captures, "
              "and the no-generator rows have no authentic reference. See the backlog for the exact blockers.", "",
              "## Native generators by vendor (top 15 by catalog size)", "", "| Vendor | Cataloged | Native | Format verified | Indexed |", "|---|---|---|---|---|"]
    for v, n in by_vendor.most_common(15):
        vo = [o for o in out if o["vendor_id"] == v]
        lines.append(f"| {v} | {n} | {sum(o['generator'] == 'NATIVE_ENGINE' for o in vo)} | {sum(o['format_verified'] == 'YES' for o in vo)} | {sum(o['indexed_evidence'] == 'YES' for o in vo)} |")
    (OUT / "pulseforge_sourcetype_coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    with open(OUT / "pulseforge_scenario_coverage.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario_id", "category", "maturity", "ecosystem"])
        for s in scenarios:
            w.writerow([s["id"], s.get("category"), s.get("maturity"), s.get("ecosystem")])
    packs, runner, live, dash_ready, det_ready = scenario_evidence()
    ids = [x["id"] for x in scenarios]
    runnable = [i for i in ids if i in packs or i in runner]
    tax = load("explorer_taxonomy.json")
    by_ind = {i["id"]: [0, 0, i["name"]] for i in tax["industries"]}
    for m in tax["scenario_industries"]:
        for ind in m["industries"]:
            by_ind[ind][0] += 1
            by_ind[ind][1] += m["scenario_id"] in runnable
    sl = ["# PulseForge Scenario Coverage", "", f"Generated {today} by `scripts/generate_coverage_report.py`. Catalog presence, "
          "runnability, live Splunk verification and maturity are separate columns of evidence.", "",
          f"| Measure | Count |", "|---|---|",
          f"| Unique catalog scenarios | {len(scenarios)} |",
          f"| Runnable (ScenarioRunner or authentic pack) | {len(runnable)} (runner {len([i for i in ids if i in runner])}, packs {len([i for i in ids if i in packs])}) |",
          f"| Contract only (not runnable) | {len(ids) - len(runnable)} |",
          f"| Live-verified in Splunk (pack scenario run, per-phase counts match, no leak) | {len([i for i in ids if i in live])} |",
          f"| E2E_VALIDATED (catalog maturity) | {mat.get('E2E_VALIDATED', 0)} |",
          f"| GOLDEN_PATH_CERTIFIED (catalog maturity) | {mat.get('GOLDEN_PATH_CERTIFIED', 0)} |",
          f"| Dashboard-verified (DASHBOARD_READY evidence) | {len(dash_ready)} |",
          f"| Detection-verified (stored evidence) | {len(det_ready)} |", "",
          "Unified-generation scenarios (25, `/api/generation/capabilities`) are not catalog rows and are counted separately in the Explorer.", "",
          "| Maturity (catalog value, not upgraded) | Count |", "|---|---|"]
    sl += [f"| {k} | {v} |" for k, v in sorted(mat.items(), key=lambda kv: -kv[1])]
    sl += ["", "Pack scenarios stay `CONTRACTED`: `FORMAT_VALIDATED` is a governed counter pinned at 2 and live byte equality is not E2E validation.", "",
           "Dashboard-verified: " + ("; ".join(dash_ready) or "none"), "", "Detection-verified: " + ("; ".join(det_ready) or "none") + ". Not Enterprise Security, CIM or Cisco TA.", "",
           "## Scenarios by approved industry (editorial mapping unless an industry pack binds it)", "", "| Industry | Mapped scenarios | Runnable |", "|---|---|---|"]
    sl += [f"| {name} | {n} | {r} |" for _, (n, r, name) in by_ind.items()]
    sl += ["", "Live-verified scenarios: " + ", ".join(sorted(i for i in ids if i in live))]
    (OUT / "pulseforge_scenario_coverage.md").write_text("\n".join(sl) + "\n", encoding="utf-8")
    print(json.dumps({"sourcetypes": summary, "scenarios": sc_summary}, indent=1))


if __name__ == "__main__":
    main(check="--check" in sys.argv)
