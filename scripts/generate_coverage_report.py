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


def ta_lab_checked():
    """Sourcetypes run through real vendor TAs in the isolated validation lab (docs/verification/evidence/ta_validation)."""
    ev = ROOT / "docs" / "verification" / "evidence" / "ta_validation" / "windows_sysmon.json"
    if not ev.exists():
        return set()
    return {e["sourcetype_emitted"] for e in json.loads(ev.read_text(encoding="utf-8"))["events"] if e["variant"] == "B" and e["indexed"]}


def fault_template_only(catalog_ids, native):
    text = (ROOT / "src" / "netspout_core" / FAULT_TEMPLATES).read_text(encoding="utf-8")
    return _literals(text, catalog_ids) - native


def raw_equality_passes(root=None):
    """Returns (byte-equal PASS sourcetypes, file-level live set, row-level proven set).

    file-level: the result file was written by a HEC-post-then-search harness (posted>0, no post_failures).
    row-level:  additionally the file records indexed_rows>0 (search returned rows) or the row itself has matches>=1.
    Earlier batches ran in the retired pf-native-lab (index idx_ta_ise_test); Batch 5/6 ran in netspout_phase4e_splunk.
    """
    passed, live, proven = set(), set(), set()
    for f in glob.glob(str((Path(root) if root else ROOT / "catalog") / "**" / "*raw_equality_results.json"), recursive=True):
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        harness_ok = data.get("posted", 0) > 0 and not data.get("post_failures")
        for row in data.get("raw_equality", []):
            if row.get("verdict") == "PASS" and row.get("sourcetype"):
                passed.add(row["sourcetype"])
                if harness_ok:
                    live.add(row["sourcetype"])
                    if (data.get("indexed_rows") or 0) > 0 or row.get("matches", 0) >= 1:
                        proven.add(row["sourcetype"])
    return passed, live, proven


def evidence_indexed(catalog_ids):
    """Sourcetypes named in committed live-run evidence files (JSON results only, not prose)."""
    found = set()
    for f in glob.glob(str(OUT / "*.json")) + glob.glob(str(OUT / "evidence" / "**" / "*.json"), recursive=True):
        if "reconciliation" in f or "demo_platform" in f or "ta_validation" in f or "splunkbase" in f:  # catalog dump / unverified platform demo: not live-ingest evidence
            continue
        text = Path(f).read_text(encoding="utf-8")
        found |= {s for s in catalog_ids if f'"{s}"' in text}
    return found


def reconciliation(ids, rows_out):
    """Origin arithmetic for the native count: pre-batch baseline (old scanner), scanner corrections, then each batch's net new."""
    from netspout_core.log_engine import SplunkLogEngine as E
    base = ROOT / "src" / "netspout_core"
    maps = {a: set(getattr(E, a)) for a in dir(E) if a.endswith("SOURCE_SOURCETYPES")}
    older = set().union(*[v for a, v in maps.items() if not a.startswith(("UNIVERSE_BATCH5", "UNIVERSE_BATCH6", "UNIVERSE_BATCH7"))]) & ids
    old_lit = set()
    for f in ("log_engine.py", "panos_generator.py", "snmp_engine.py", "gnmi_engine.py"):  # the Phase 3-4 scanner's exact module list and patterns
        text = (base / f).read_text(encoding="utf-8")
        for st in ids:
            q = re.escape(st)
            if re.search(r"sourcetype\s*=\s*[\"']" + q + r"[\"']", text) or re.search(r"[\"'](?:sourcetype|splunk_sourcetype)[\"']\s*:\s*[\"']" + q + r"[\"']", text):
                old_lit.add(st)
    baseline = older | old_lit
    now_native = {o["sourcetype"] for o in rows_out if o["generator"] == "NATIVE_ENGINE"}
    ub5 = set(maps.get("UNIVERSE_BATCH5_SOURCE_SOURCETYPES", ())) & ids
    ub6 = set(maps.get("UNIVERSE_BATCH6_SOURCE_SOURCETYPES", ())) & ids
    ub7 = set(maps.get("UNIVERSE_BATCH7_SOURCE_SOURCETYPES", ())) & ids
    corrections = (now_native - ub5 - ub6 - ub7) - baseline
    b5_new = ub5 - baseline - corrections
    b6_new = ub6 - baseline - corrections - ub5
    b7_new = ub7 - baseline - corrections - ub5 - ub6
    return {"pre_batch_baseline": len(baseline), "discovery_corrections": sorted(corrections), "batch5_registered": len(ub5),
            "batch5_net_new": len(b5_new), "batch5_already_native": sorted(ub5 & (baseline | corrections)), "batch6_registered": len(ub6),
            "batch6_net_new": len(b6_new), "batch7_registered": len(ub7), "batch7_net_new": len(b7_new),
            "sum": len(baseline) + len(corrections) + len(b5_new) + len(b6_new) + len(b7_new), "now_native": len(now_native)}


def lost_grounding_count():
    """Active catalog sourcetypes that no longer get an unrelated vendor-level sample in Single Event mode."""
    from netspout_core.generator_modes import TelemetryGeneratorService
    from netspout_core.vendor_catalog import get_vendor_by_id
    svc = TelemetryGeneratorService()
    rows = [r for r in svc.catalog._sourcetypes if r.get("status") == "active"]
    per_vendor = {}
    for r in rows:
        per_vendor[r["vendor_id"]] = per_vendor.get(r["vendor_id"], 0) + 1
    n = 0
    for r in rows:
        if svc._universe_source(r["splunk_sourcetype"])[0]:
            continue
        events, _, _ = svc.get_grounded_samples(r["splunk_sourcetype"], vendor_id=r["vendor_id"])
        vendor = get_vendor_by_id(r["vendor_id"])
        n += (not events) and bool(vendor and vendor.get("sample_events")) and per_vendor[r["vendor_id"]] > 1
    return n


def reachability(ids, native):
    """Which customer-facing path can actually emit each native sourcetype (not just 'an engine formatter exists')."""
    from netspout_core.authentic_scenario_packs import SCENARIO_PACK_IDS, run_scenario_pack
    from netspout_core.log_engine import SplunkLogEngine as E
    from netspout_core.scenario_runner import SUPPORTED_SCENARIO_IDS
    single = set()
    for a in dir(E):
        if a.startswith("UNIVERSE_BATCH") and a.endswith("SOURCE_SOURCETYPES"):
            single |= set(getattr(E, a))
    pack = set()
    for sid in SCENARIO_PACK_IDS:
        pack |= {e.sourcetype for e in run_scenario_pack(sid, "coverage")}
    runner = set()
    for sc in load("scenarios.json"):
        if sc["id"] in SUPPORTED_SCENARIO_IDS:
            runner |= set(sc.get("sourcetypes", []))
    native &= ids
    return {"single_event_native": len(native & single), "scenario_pack_emitted": len(native & pack),
            "runner_scenario_listed": len(native & runner), "no_customer_path": sorted(native - single - pack - runner)}


def scenario_evidence():
    """Runnable / live-verified / dashboard / detection evidence for catalog scenarios, from committed artifacts only."""
    from netspout_core.authentic_scenario_packs import SCENARIO_PACK_IDS
    from netspout_core.incident_packs import incident_ids
    from netspout_core.scenario_runner import SUPPORTED_SCENARIO_IDS
    live = {}
    for f in glob.glob(str(ROOT / "catalog" / "*live_raw_equality_results.json")) + glob.glob(str(OUT / "evidence" / "incident_packs" / "live_results.json")):
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
    return set(SCENARIO_PACK_IDS) | set(incident_ids()), set(SUPPORTED_SCENARIO_IDS), live, dashboard_ready, detection


def replay_evidence(ids):
    """Replay packs, the recorded sources they use, and which of those the isolated-lab validation verified (replay_live.json)."""
    packs = load("replay_packs.json")["packs"]
    srcs = {x["id"]: x for x in load("replay_sources.json")["sources"]}
    ev_path = OUT / "evidence" / "replay" / "replay_live.json"
    ev = json.loads(ev_path.read_text(encoding="utf-8")) if ev_path.exists() else {}
    verified = set(ev.get("packs_indexed_verified", []))
    used = {ph["source"]["source_id"] for p in packs if p["id"] in verified for ph in p["phases"] if ph["source"]["kind"] == "replay"}
    sts = {srcs[u]["sourcetype"] for u in used if srcs[u].get("sourcetype")}
    return packs, srcs, verified, sorted(sts & ids), sorted(sts - ids)


def explorer_view():
    """The Explorer's own inventory (unified generation + catalog + incident packs + documented candidates), so reports never disagree with the product."""
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import _explorer
    return _explorer()


def main(check=False):
    rows = load("sourcetypes.json")
    ids = {r["splunk_sourcetype"] for r in rows}
    cat_ids = set(ids)  # `ids` is reused for scenario ids further down
    native = engine_sourcetypes(ids)
    fmt, live_fmt, proven_fmt = raw_equality_passes()
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
        "ta_parsing_checked_isolated_lab": len(ta_lab_checked()),
        "independently_indexed": sum(o["indexed_evidence"] == "YES" for o in out),
        "continuous_replay_verified": len(replay_evidence(cat_ids)[3]),
    }
    scenarios = load("scenarios.json")
    mat = Counter(s.get("maturity") for s in scenarios)
    gp = load("golden_path_evidence.json").get("golden_paths", [])
    det = load("phase13a_validation_evidence.json").get("validations", [])
    det_ok = [v for v in det if v.get("status") == "POSITIVE_CASE_VALIDATED"]
    sc_summary = {"catalog_scenarios": len(scenarios), "by_maturity": dict(mat), "golden_path_records": len(gp), "detection_verified": len(det_ok)}
    rec = reconciliation(ids, out)
    assert rec["sum"] == rec["now_native"] == summary["native_generators"], rec  # the origin arithmetic must close exactly
    parts = {t: {o["sourcetype"] for o in out if o["generator"] == t} for t in ("NATIVE_ENGINE", "SAMPLE_REPLAY", "NONE")}
    assert sum(len(v) for v in parts.values()) == len(ids) == len(out) and not (parts["NATIVE_ENGINE"] & parts["SAMPLE_REPLAY"])
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
                       ("Vendor TA validated (full or partial; Cisco ISE only, earlier lab)", "ta_validated_or_partial"),
                       ("Parsed by a real vendor TA in the isolated lab this phase (extraction of emitted fields, timestamps and tags; not CIM or detections)", "ta_parsing_checked_isolated_lab"),
                       ("Independently indexed (live evidence)", "independently_indexed"),
                       ("Continuous-replay-verified (canonical sourcetype replayed from an authentic recording in a pack verified live; not TA/CIM)", "continuous_replay_verified")):
        lines.append(f"| {label} | {summary[key]} | {100 * summary[key] / n:.1f}% |")
    lines += ["", "Tier definitions are in the script header. `TA validated` counts only a parser that was installed and exercised; "
              "mapping-only assessments are not counted. `Sample replay only` is recorded-event replay, not a vendor-native formatter.", "",
              "## Vendors with the most uncovered sourcetypes", "", "| Vendor | Cataloged | Native generator |", "|---|---|---|"]
    gaps = sorted(by_vendor, key=lambda v: -(by_vendor[v] - nat_vendor[v]))[:15]
    for v in gaps:
        lines.append(f"| {v} | {by_vendor[v]} | {nat_vendor[v]} |")
    fv = {o["sourcetype"] for o in out if o["format_verified"] == "YES"}
    ix = {o["sourcetype"] for o in out if o["indexed_evidence"] == "YES"}
    reach = reachability(ids, set(parts["NATIVE_ENGINE"]))
    lost_n = lost_grounding_count()
    fault = sorted(fault_template_only(ids, native))
    b5 = {x["splunk_sourcetype"] for x in load("universe_batch5.json")["sources"]} if (ROOT / "catalog" / "universe_batch5.json").exists() else set()
    lines += ["", "## Reconciliation (origin arithmetic; internal-consistency check)", "",
              "| Component | Count |", "|---|---|",
              f"| Pre-Batch-5 native baseline (re-derived with the ORIGINAL scanner rules and the pre-Batch-5 registries; not a recorded historical number) | {rec['pre_batch_baseline']} |",
              f"| + Scanner discovery corrections (generators that already existed) | +{len(rec['discovery_corrections'])} ({', '.join(rec['discovery_corrections'])}) |",
              f"| + Batch 5 net new (registered {rec['batch5_registered']}; already native: {', '.join(rec['batch5_already_native']) or 'none'}) | +{rec['batch5_net_new']} |",
              f"| + Batch 6 net new (registered {rec['batch6_registered']}) | +{rec['batch6_net_new']} |",
              f"| + Batch 7 net new (registered {rec['batch7_registered']}) | +{rec['batch7_net_new']} |",
              f"| **Native generators now** | **{rec['now_native']}** |", "",
              "The sum closes largely by construction (corrections and batch net-new are defined as set differences), so it checks that no sourcetype is counted twice or dropped; "
              "it is not an independent historical audit. Registries added after Batch 6 would be treated as part of the baseline until this function is extended.", "",
              "Partition: native + sample-replay-only + no-generator = %d + %d + %d = %d (disjoint)." % (len(parts['NATIVE_ENGINE']), len(parts['SAMPLE_REPLAY']), len(parts['NONE']), len(ids)), "",
              "Evidence overlaps (a sourcetype is counted once per measure; measures are independent):", "",
              "| Overlap | Count |", "|---|---|",
              f"| Byte-verified AND native | {len(fv & parts['NATIVE_ENGINE'])} |",
              f"| Byte-verified but NOT native (verified through a retired or fixture path) | {len(fv - parts['NATIVE_ENGINE'])} |",
              f"| Native but never byte-verified | {len(parts['NATIVE_ENGINE'] - fv)} |",
              f"| Independently indexed AND byte-verified | {len(ix & fv)} |",
              f"| Independently indexed but NOT byte-verified (run-evidence files only) | {len(ix - fv)} |",
              f"| Byte-verified but no live-indexing record (offline/current-fixture equality only) | {len(fv - ix)} |",
              f"| Independently indexed with ROW-LEVEL proof (indexed_rows>0 or per-row matches>=1) | {len(proven_fmt)} |",
              f"| Independently indexed on FILE-LEVEL harness evidence only (older result files without row counts) | {len(live_fmt - proven_fmt)} |", "",
              "Definition change: the earlier report counted only result files whose NAME contained 'live' (105). Every result file is written by a harness that posts to HEC "
              "and searches Splunk, so the measure now counts all of them (136 = file-level), and the row above separates what has row-level proof. The increase is a "
              "correction of an undercount, not new indexing.", "",
              "## Reachability of native generators (a formatter existing is not the same as a customer being able to run it)", "",
              "| Customer-facing path | Native sourcetypes reachable |", "|---|---|",
              f"| Single Event / Sourcetype generator modes (native registries UB1-UB6) | {reach['single_event_native']} |",
              f"| Authentic scenario packs (`/api/generate/scenario-pack`, Explorer `scenario_pack`) emit them | {reach['scenario_pack_emitted']} |",
              f"| Listed by a ScenarioRunner scenario (label-level; the runner may use a different formatter) | {reach['runner_scenario_listed']} |",
              f"| **Native but on none of the above** | **{len(reach['no_customer_path'])}** |", "",
              "Native but not reachable from any listed path: " + (", ".join(reach["no_customer_path"][:40]) + (" ..." if len(reach["no_customer_path"]) > 40 else "")), "",
              f"Single Event / Sourcetype modes serve native registries for UB1-UB6 sourcetypes only; elsewhere they serve sample files. {lost_n} active catalog sourcetypes used to be answered with an unrelated vendor-level sample and now report TELEMETRY_NOT_GROUNDED (the fallback is limited to vendors with a single active sourcetype). The script does not verify which other path serves a given sourcetype beyond the three rows above.", "",
              "## Reconciliation notes", "",
              "* Batch 5 registers 31 sourcetypes but added 30 to the count: `cisco:sdwan:BGP-5-ADJCHANGE` already had a native formatter "
              "(`format_cisco_sdwan_bgp_log`), so it now has two generators. Not a counting defect.",
              "* Each of the six corrections was inspected by hand, not just pattern-matched: `pan:system` is emitted by `PanOsGenerator` (`SOURCETYPE_BY_TYPE['SYSTEM']` used when building the LogEntry, 17 documented fields); "
              "`netspout:snmp:trap` / `netspout:snmp:poll` are set on the normalized events built in `snmp_splunk_e2e.py` (live E2E evidence exists); `cisco:duo:remote:vpn`, `cisco:catalyst:clienthealth` and "
              "`meraki:assurancealerts` are the default `sourcetype` of `format_cisco_duo_vpn_log`, `format_cisco_catalyst_wlan_rf_log` and `format_meraki_alert_log` in `log_engine.py`. "
              "Pattern matching alone would also hit comments and lookups, so any future correction needs the same inspection.",
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
    pack_ids = [i for i in ids if i in packs]
    sl += ["", "## Maturity gates (unchanged; definitions from docs/architecture/NETSPOUT_CANONICAL_SCENARIO_REGISTRY.md)", "",
           "| Tier | Gate | Count now |", "|---|---|---|",
           f"| GOLDEN_PATH_CERTIFIED | Independently verified through live Splunk acceptance with 100% telemetry observation completeness, zero developer knowledge, clean validation | {mat.get('GOLDEN_PATH_CERTIFIED', 0)} |",
           f"| E2E_VALIDATED | Wired to multi-vendor topology graphs with deterministic simulation runners and passing contract rules; pending independent acceptance retest | {mat.get('E2E_VALIDATED', 0)} |",
           f"| FORMAT_VALIDATED | Baseline traffic emitting compliant wire formats (governed counter, pinned) | {mat.get('FORMAT_VALIDATED', 0)} |",
           f"| CONTRACTED | Blueprint with schema definitions, expected observations; implementation may be absent | {mat.get('CONTRACTED', 0)} |", "",
           f"No scenario was promoted in this pass. The {len(pack_ids)} authentic observation packs are `CONTRACTED`: they have live byte-equality and per-phase indexing evidence "
           "(batch 1-6 result files) but are not wired to topology graphs, have no independent acceptance retest, no dashboard and no detection, so they meet none of the higher gates. "
           "Byte-equal bytes or successful ingestion never promote a scenario.", "",
           "| Group | Scenarios | Evidence now | Missing for the next tier |", "|---|---|---|---|",
           f"| Authentic packs (wave*, ub1-ub6) | {len(pack_ids)} | byte-equal families; per-phase counts for {len([i for i in pack_ids if i in live])} packs | topology wiring, runner determinism contract, independent acceptance retest |",
           f"| ScenarioRunner scenarios | {len([i for i in ids if i in runner])} | GOLDEN {mat.get('GOLDEN_PATH_CERTIFIED', 0)} / E2E {mat.get('E2E_VALIDATED', 0)} per catalog | E2E_VALIDATED ones need the independent acceptance retest |",
           f"| Contract-only | {len(ids) - len(runnable)} | none | any executable telemetry; no Run action is offered |", "",
           "Pack scenarios stay `CONTRACTED`: `FORMAT_VALIDATED` is a governed counter pinned at 2 and live byte equality is not E2E validation.", "",
           "Dashboard-verified: " + ("; ".join(dash_ready) or "none"), "", "Detection-verified: " + ("; ".join(det_ready) or "none") + ". Not Enterprise Security, CIM or Cisco TA.", "",
           "## Scenarios by approved industry (editorial mapping unless an industry pack binds it)", "", "| Industry | Mapped scenarios | Runnable |", "|---|---|---|"]
    sl += [f"| {name} | {n} | {r} |" for _, (n, r, name) in by_ind.items()]
    sl += ["", "Live-verified scenarios: " + ", ".join(sorted(i for i in ids if i in live))]
    ex = explorer_view()
    entries = [e for e in ex.all_entries() if e["kind"] == "operational"]
    by_engine = Counter(e["engine"] for e in entries)
    by_tier = Counter(e["maturity"]["tier"] for e in entries)
    sec = ex.facets()["security"]
    native_now = {o["sourcetype"] for o in out if o["generator"] == "NATIVE_ENGINE"}
    sl += ["", "## Unique scenario inventory (the Explorer's own view; nothing counted twice)", "",
           "| Measure | Count |", "|---|---|",
           f"| Unique operational definitions (executable + documented candidates) | {len(entries)} |",
           f"| Runnable (a real generator and Run path exist) | {sum(e['runnable'] for e in entries)} |",
           f"| Cataloged candidates only (documented; no generator or contract; never runnable) | {by_tier['CATALOGED']} |",
           f"| Contract-only (catalog contracts without executable telemetry; no Run action) | {sum(1 for e in entries if not e['runnable'] and e['maturity']['tier'] != 'CATALOGED')} |",
           f"| Live-verified in Splunk (counts and, for incident packs, mstats values checked independently) | {sum(e['live_verified'] for e in entries)} |",
           f"| Dashboard-verified | {sum(e['dashboard_verified'] for e in entries)} |",
           f"| Security analytic stories (reference stories; NOT counted as executable) | {sec['total']} |",
           f"| Security stories with a runnable workflow (runtime-approved detection) | {sec['demo_ready']} |",
           f"| Detection-verified | {len(det_ready)} |",
           f"| Duplicate candidates removed (already represented by an executable entry) | {len(ex.duplicate_candidates)} |", "",
           "By engine: " + ", ".join(f"{k} {v}" for k, v in sorted(by_engine.items())) + ". By tier: " + ", ".join(f"{k} {v}" for k, v in sorted(by_tier.items())) + ".", "",
           "Incident packs (27 network + 10 telecom) emit NetSpout-defined MODELED telemetry (`netspout:*`), not vendor-native formats; they stay CONTRACTED. "
           "Cataloged candidates come from `catalog/scenario_candidates.json` (MIT community use-case catalog pinned to a commit, plus Cisco 100 definitions that are not execution-enabled).", "",
           "## Replay packs (scenario packs on the continuous-replay engine)", "",
           "Each pack mixes recorded (authentic) phases and/or existing native packs. Tier stays CONTRACTED: events indexing is evidence of delivery, not E2E validation, "
           "a dashboard or a detection. Independent recordings are aligned in time only (TEMPORAL_ONLY).", "",
           "| Pack | Category | Source mode | Phases | Correlation | Indexed-verified (isolated lab) | Dashboard | Detection | Industries (editorial) |", "|---|---|---|---|---|---|---|---|---|"]
    rpacks, rsrcs, rverified, rcanon, rnoncanon = replay_evidence(cat_ids)
    from netspout_core import replay_packs as _rp
    for p_ in rpacks:
        modes = sorted({ph["source"]["kind"] for ph in p_["phases"]})
        sl.append(f"| {p_['id']} | {p_['category']} | {'both' if len(modes) == 2 else modes[0]} | {len(p_['phases'])} | {_rp.correlation_level(p_)} | {'YES' if p_['id'] in rverified else 'NO'} | none | none | {', '.join(p_['industries'])} |")
    sl += ["", f"Replay-verified canonical sourcetypes ({len(rcanon)}): {', '.join(rcanon)}. Recorded sources whose sourcetype is not a catalog canonical name ({len(rnoncanon)}): {', '.join(rnoncanon) or 'none'} (replayable, not counted as coverage).", "",
           "## Industry scenario packs added 2026-10-30 (26; all native sequences of existing authentic packs, run by the replay engine)", "",
           "Framing by industry/sub-industry is editorial; telemetry and in-pack correlation are authentic; constituent packs are related by time only. "
           "Maturity CONTRACTED. `Panels` = every panel query returned rows for a live run in the isolated lab (not a Dashboard Studio object). "
           "Detections are not claimed (no add-on, CIM or ES content installed).", "",
           "| Scenario | Industry / sub-industry | Kind | Constituent native packs | Sourcetypes | Indexed | Panels |", "|---|---|---|---|---|---|---|"]
    rpanels = set(json.loads((OUT / "evidence" / "replay" / "replay_live.json").read_text(encoding="utf-8")).get("packs_panels_populated", [])) if (OUT / "evidence" / "replay" / "replay_live.json").exists() else set()
    for p_ in [x for x in rpacks if x["id"].startswith("ind_")]:
        sl.append(f"| {p_['id']} | {p_['industries'][0]} / {p_['subindustry']} | {p_['kind']} | {', '.join(ph['source']['pack'] for ph in p_['phases'])} | {len(p_['required_sourcetypes'])} | {'YES' if p_['id'] in rverified else 'NO'} | {'YES' if p_['id'] in rpanels else 'NO'} |")
    sl += ["", "**Missing inputs (not reconstructed, not claimed integrated):** the original 100 financial-services and 100 telecom use-case libraries. Their IDs are still needed; none of the scenarios above came from them.", "",
           "Replay sample corpus: 10 vendored authentic recordings (`catalog/replay_sources.json`). The Ollama server log was excluded because it mixes three timestamp formats. "
           "SA-Eventgen was not evaluated against its version-specific spec (not installed in any lab); the PulseForge replay engine was reused.", "",
           "## 18-industry coverage matrix", "",
           "Columns are separate evidence: documented is not runnable, runnable is not verified, verified is not TA-parsed or detected. Mappings are editorial unless the "
           "source labels the industry (`*` in the Explorer).", "",
           "| Industry | Documented (all) | Cataloged only | Contracted | Runnable | Independently indexed | Panel queries populated | Dashboard-verified | Curated stories | Stories runnable | Detections verified | Named sourcetypes without a native generator | Government subdomains covered |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in ex.industries():
        mine = [e for e in entries if any(i["id"] == r["id"] for i in e["industries"])]
        named = {st for e in mine for st in e.get("sourcetypes", []) if st not in native_now and not st.startswith("netspout:")}
        sl.append(f"| {r['name']} | {r['scenarios_total']} | {r['scenarios_cataloged_only']} | {r['scenarios_contracted']} | {r['scenarios_runnable']} | {r['scenarios_live_verified']} | {r['scenarios_panels_populated']} | {r['scenarios_dashboard_verified']} | {r['security_stories_curated']} | {r['security_stories_runnable']} | {r['security_detections_verified']} | {len(named)} | {', '.join(s.replace('gov-', '') for s in r['subdomains_with_scenarios']) or '-'} |")
    sl += ["", "Curated stories are Splunk Analytic Stories whose own text names the sector as a threat target (basis NARRATIVE_TARGET_SECTOR) and whose original research.splunk.com page was verified (HTTP 200); "
           "they are NOT executable: only a story with a runtime-approved detection is runnable, and the single detection-verified item (React2Shell) is not curated to an industry. "
           "Technology/SaaS, media, non-profit and agriculture have no story whose text names the sector and whose link resolves. "
           "Government subdomains: State/Local, National Security and Critical Infrastructure have editorial or source-labeled entries; **Federal Civilian and Compliance has none** (no authoritative source selected). "
           "TA validation is not tracked per industry: only Windows/Sysmon channels were TA-checked (see the TA matrix). Industries whose documented scenarios have no runnable counterpart "
           "(for example transportation, media, aerospace/defense, agriculture, real estate, insurance, non-profit) need authentic telemetry sources before they can become runnable."]
    (OUT / "pulseforge_scenario_coverage.md").write_text("\n".join(sl) + "\n", encoding="utf-8")
    print(json.dumps({"sourcetypes": summary, "scenarios": sc_summary}, indent=1))


if __name__ == "__main__":
    main(check="--check" in sys.argv)
