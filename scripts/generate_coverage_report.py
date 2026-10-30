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


def engine_sourcetypes(catalog_ids):
    from netspout_core.log_engine import SplunkLogEngine as E
    mapped = set()
    for attr in dir(E):
        if attr.endswith("SOURCE_SOURCETYPES"):
            mapped |= set(getattr(E, attr))
    literal = set()
    for f in ("log_engine.py", "panos_generator.py", "snmp_engine.py", "gnmi_engine.py"):
        text = (ROOT / "src" / "netspout_core" / f).read_text(encoding="utf-8")
        literal |= set(re.findall(r"sourcetype\s*=\s*[\"']([^\"']+)[\"']", text))
        literal |= set(re.findall(r"[\"'](?:sourcetype|splunk_sourcetype)[\"']\s*:\s*[\"']([^\"']+)[\"']", text))
    return (mapped | literal) & catalog_ids


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
    (OUT / "pulseforge_sourcetype_coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    with open(OUT / "pulseforge_scenario_coverage.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario_id", "category", "maturity", "ecosystem"])
        for s in scenarios:
            w.writerow([s["id"], s.get("category"), s.get("maturity"), s.get("ecosystem")])
    sl = ["# PulseForge Scenario Coverage", "", f"Generated {today} by `scripts/generate_coverage_report.py`.", "",
          f"Cataloged scenarios: **{len(scenarios)}**", "", "| Maturity (catalog value, not upgraded) | Count |", "|---|---|"]
    sl += [f"| {k} | {v} |" for k, v in sorted(mat.items(), key=lambda kv: -kv[1])]
    sl += ["", f"Golden-path evidence records: {len(gp)}. Detection-verified security validations (`POSITIVE_CASE_VALIDATED`): {len(det_ok)}.",
           "Dashboard readiness is recorded per run by the dashboard service, not in this catalog. Security stories need detection "
           "verification, not dashboards. Industry coverage is in `catalog/explorer_taxonomy.json` (approved 18 industries, editorial mappings)."]
    (OUT / "pulseforge_scenario_coverage.md").write_text("\n".join(sl) + "\n", encoding="utf-8")
    print(json.dumps({"sourcetypes": summary, "scenarios": sc_summary}, indent=1))


if __name__ == "__main__":
    main(check="--check" in sys.argv)
